"""
Links a Telegram chat_id to a customer_id, via the one-time code flow:
website OAuth completes -> owner is shown a short code -> they send it to
the bot -> this module resolves the code to a customer_id and writes the
link.

The one-time code itself is generated/stored by the website's backend
(or this same backend, if the website calls into it) — this module only
handles the *lookup* side once the code arrives via Telegram.
"""
import secrets

from app.db import get_pool

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15


async def create_link_code(customer_id: str) -> str:
    """Called right after website OAuth completes. Store the code somewhere
    short-lived — reusing gbp_credentials' customer row via a small extra
    table is cleanest; shown inline here as a lightweight approach using a
    dedicated table (add to migrations if you go this route)."""
    code = secrets.token_hex(CODE_LENGTH // 2).upper()
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO telegram_link_codes (code, customer_id, expires_at)
        VALUES ($1, $2, now() + make_interval(mins => $3))
        """,
        code,
        customer_id,
        CODE_TTL_MINUTES,
    )
    return code


async def resolve_link_code(code: str, chat_id: int) -> str | None:
    """Called from the Telegram webhook when a message looks like a link
    code. Returns the customer_id on success, None if invalid/expired."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT customer_id FROM telegram_link_codes
                WHERE code = $1 AND expires_at > now() AND used_at IS NULL
                FOR UPDATE
                """,
                code,
            )
            if row is None:
                return None

            customer_id = str(row["customer_id"])

            await conn.execute(
                "UPDATE telegram_link_codes SET used_at = now() WHERE code = $1",
                code,
            )
            await conn.execute(
                """
                INSERT INTO telegram_chat_links (chat_id, customer_id, link_code)
                VALUES ($1, $2, $3)
                ON CONFLICT (chat_id) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    link_code = EXCLUDED.link_code,
                    linked_at = now()
                """,
                chat_id,
                customer_id,
                code,
            )
            return customer_id


async def get_customer_for_chat(chat_id: int) -> str | None:
    """Called on every incoming Telegram message to resolve identity."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT customer_id FROM telegram_chat_links WHERE chat_id = $1",
        chat_id,
    )
    return str(row["customer_id"]) if row else None
