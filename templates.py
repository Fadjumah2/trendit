"""
Backend-owned message templates. The agent produces post content; this
module wraps that content in whatever Telegram needs to render it well
(HTML formatting + inline keyboards). Keep ALL Telegram-specific string
formatting here — nowhere else.
"""


def draft_preview(post_id: str, post_type: str, content: dict) -> tuple[str, dict]:
    """Returns (text, reply_markup) for a new draft awaiting owner action."""
    title = content.get("title", "")
    body = content.get("body", "")
    cta = content.get("cta", "")

    text = (
        f"<b>New {post_type.capitalize()} Post Draft</b>\n\n"
        f"<b>{_escape(title)}</b>\n"
        f"{_escape(body)}\n\n"
        f"<i>CTA: {cta}</i>"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{post_id}"},
                {"text": "✏️ Edit", "callback_data": f"edit:{post_id}"},
                {"text": "⏭ Skip", "callback_data": f"skip:{post_id}"},
            ]
        ]
    }
    return text, reply_markup


def published_confirmation(post_type: str, gbp_post_id: str) -> str:
    return (
        f"✅ Your {post_type} post has been published to Google Business Profile.\n"
        f"<i>Reference: {gbp_post_id}</i>"
    )


def validator_flagged(errors: list[str]) -> str:
    error_lines = "\n".join(f"• {_escape(e)}" for e in errors)
    return (
        "⚠️ This draft needs a fix before it can be published:\n\n"
        f"{error_lines}\n\n"
        "Reply with your edit, or send /skip to discard this draft."
    )


def generic_error(context: str = "") -> str:
    suffix = f" ({_escape(context)})" if context else ""
    return f"⚠️ Something went wrong{suffix}. Please try again, or contact support if this keeps happening."


def linking_success(business_name: str | None = None) -> str:
    name = f" for <b>{_escape(business_name)}</b>" if business_name else ""
    return f"✅ Linked{name}! You'll receive post drafts here going forward."


def linking_invalid_code() -> str:
    return "That code doesn't match an active link request. Please check the website and try again."


def _escape(text: str) -> str:
    """Minimal HTML escaping for Telegram's HTML parse_mode."""
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
