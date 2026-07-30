"""
Service for sending notifications to customers.
"""
import json
from app.db import get_pool
from app.config import settings
from app.email import client as email_client
from app.email import templates as email_templates
from app.telegram import client as tg_client
from app.telegram import templates as tg_templates

async def send_draft_for_approval(post_id: str) -> None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT 
            ph.post_type, 
            ph.draft_content, 
            c.email,
            tcl.chat_id
        FROM post_history ph
        JOIN customers c ON ph.customer_id = c.customer_id
        LEFT JOIN telegram_chat_links tcl ON c.customer_id = tcl.customer_id
        WHERE ph.id = $1
        """,
        post_id,
    )
    
    if row is None:
        raise ValueError(f"post_history row {post_id} not found")
        
    post_type = row["post_type"]
    draft_content_raw = row["draft_content"]
    if isinstance(draft_content_raw, str):
        draft_content = json.loads(draft_content_raw)
    else:
        draft_content = dict(draft_content_raw)
        
    customer_email = row["email"]
    chat_id = row["chat_id"]
    
    # 1. Email Notification (Primary)
    subject, html_body = email_templates.draft_preview_email(
        post_id=post_id,
        post_type=post_type,
        draft_content=draft_content,
        backend_url=settings.BACKEND_URL
    )
    
    await email_client.send_email(
        to=customer_email,
        subject=subject,
        html=html_body
    )

    # 2. Telegram Notification (Parallel, if configured)
    if chat_id:
        tg_text, tg_markup = tg_templates.draft_preview(
            post_id=post_id,
            post_type=post_type,
            content=draft_content
        )
        await tg_client.send_message(
            chat_id=chat_id,
            text=tg_text,
            reply_markup=tg_markup
        )

async def send_connection_confirmation(customer_id: str, location_id: str) -> None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT c.email, c.business_name, tcl.chat_id
        FROM customers c
        LEFT JOIN telegram_chat_links tcl ON c.customer_id = tcl.customer_id
        WHERE c.customer_id = $1
        """,
        customer_id,
    )
    if row is None:
        return

    subject, html_body = email_templates.connection_confirmed_email(
        business_name=row["business_name"] or "your business",
        location_id=location_id,
    )
    await email_client.send_email(to=row["email"], subject=subject, html=html_body)

    if row["chat_id"]:
        await tg_client.send_message(
            chat_id=row["chat_id"],
            text=tg_templates.connection_confirmed(location_id),
        )
