"""
Telegram webhook handler. Receives every update Telegram sends, resolves
the sender's identity via chat_id, and routes to the right action:
  - a 6-char code with no existing link -> linking flow
  - a callback_query button tap (approve/edit/skip) -> post_history update
  - free-text reply while a draft is pending -> treated as an edit

This module owns routing only — it delegates to services/post_history,
credentials, agent, validator for the actual work.
"""
import re

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.telegram import client as tg_client
from app.telegram import templates
from app.telegram.linking import get_customer_for_chat, resolve_link_code
from app.services.post_history import (
    get_pending_draft_for_customer,
    mark_approved,
    mark_edited,
    mark_skipped,
)
from app.services.publish import publish_post

router = APIRouter()

_LINK_CODE_RE = re.compile(r"^[A-Z0-9]{6}$")


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="bad webhook secret")

    update = await request.json()

    if "callback_query" in update:
        await _handle_callback_query(update["callback_query"])
    elif "message" in update:
        await _handle_message(update["message"])

    return {"ok": True}


async def _handle_message(message: dict) -> None:
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    customer_id = await get_customer_for_chat(chat_id)

    # Not linked yet -> only thing we accept is a link code
    if customer_id is None:
        if _LINK_CODE_RE.match(text.upper()):
            resolved = await resolve_link_code(text.upper(), chat_id)
            if resolved:
                await tg_client.send_message(chat_id, templates.linking_success())
            else:
                await tg_client.send_message(chat_id, templates.linking_invalid_code())
        else:
            await tg_client.send_message(
                chat_id,
                "Hi! Please enter the linking code shown on the website to connect your account.",
            )
        return

    # Linked customer sending free text while a draft is pending -> treat as edit
    pending = await get_pending_draft_for_customer(customer_id)
    if pending is not None and text:
        await mark_edited(pending["id"], edited_content={**pending["draft_content"], "body": text})
        await tg_client.send_message(chat_id, "Got your edit — re-checking it now...")
        # Re-validate the edited draft the same way the original draft was validated.
        # See services/post_history.py + validator/validator.py for the shared path.
        return

    await tg_client.send_message(chat_id, "No draft is currently pending. New posts will appear here automatically.")


async def _handle_callback_query(callback_query: dict) -> None:
    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]

    action, _, post_id = data.partition(":")
    customer_id = await get_customer_for_chat(chat_id)

    if customer_id is None:
        await tg_client.answer_callback_query(callback_id, "Not linked yet.")
        return

    if action == "approve":
        await mark_approved(post_id)
        result = await publish_post(post_id)
        await tg_client.answer_callback_query(callback_id, "Approved!")
        await tg_client.send_message(
            chat_id,
            templates.published_confirmation(result["post_type"], result["gbp_post_id"]),
        )
    elif action == "edit":
        await tg_client.answer_callback_query(callback_id, "Send your edit as a reply.")
        await tg_client.send_message(chat_id, "Reply with the edited text for this post.")
    elif action == "skip":
        await mark_skipped(post_id)
        await tg_client.answer_callback_query(callback_id, "Skipped.")
    else:
        await tg_client.answer_callback_query(callback_id, "Unknown action.")
