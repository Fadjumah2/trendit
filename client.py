"""
Thin wrapper around the Telegram Bot API. The agent never calls this
directly — it only ever produces post *content*. This module + templates.py
own all Telegram-specific formatting.
"""
import httpx

from app.config import settings

_BASE = f"{settings.TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{_BASE}/sendMessage", json=payload)
        resp.raise_for_status()
        return resp.json()


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> dict:
    """Acknowledges a button tap so Telegram stops showing the loading spinner."""
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{_BASE}/answerCallbackQuery", json=payload)
        resp.raise_for_status()
        return resp.json()


async def set_webhook(webhook_url: str, secret_token: str) -> dict:
    """One-time setup call — see README for how/when to run this."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{_BASE}/setWebhook",
            json={"url": webhook_url, "secret_token": secret_token},
        )
        resp.raise_for_status()
        return resp.json()
