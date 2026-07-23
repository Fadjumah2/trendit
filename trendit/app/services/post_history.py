"""
CRUD around post_history — every draft, its validator result, and the
owner's decision. This is both the audit trail and the source of approved
posts fed back as few-shot examples (see agent/content_profile.py).
"""
from app.db import get_pool


async def create_draft(customer_id: str, location_id: str, post_type: str, draft_content: dict) -> str:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO post_history (customer_id, location_id, post_type, draft_content)
        VALUES ($1, $2, $3, $4::jsonb)
        RETURNING id
        """,
        customer_id,
        location_id,
        post_type,
        draft_content,
    )
    return str(row["id"])


async def save_validator_result(post_id: str, validator_result: dict, fixed_content: dict | None) -> None:
    pool = get_pool()
    if fixed_content:
        await pool.execute(
            """
            UPDATE post_history
            SET validator_result = $2::jsonb, draft_content = $3::jsonb, updated_at = now()
            WHERE id = $1
            """,
            post_id,
            validator_result,
            fixed_content,
        )
    else:
        await pool.execute(
            "UPDATE post_history SET validator_result = $2::jsonb, updated_at = now() WHERE id = $1",
            post_id,
            validator_result,
        )


async def get_pending_draft_for_customer(customer_id: str) -> dict | None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, location_id, post_type, draft_content
        FROM post_history
        WHERE customer_id = $1 AND owner_decision = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        customer_id,
    )
    return dict(row) if row else None


async def mark_approved(post_id: str) -> None:
    pool = get_pool()
    await pool.execute(
        """
        UPDATE post_history
        SET owner_decision = 'approved', final_content = draft_content, updated_at = now()
        WHERE id = $1
        """,
        post_id,
    )


async def mark_edited(post_id: str, edited_content: dict) -> None:
    pool = get_pool()
    await pool.execute(
        """
        UPDATE post_history
        SET owner_decision = 'edited', draft_content = $2::jsonb, updated_at = now()
        WHERE id = $1
        """,
        post_id,
        edited_content,
    )


async def mark_skipped(post_id: str) -> None:
    pool = get_pool()
    await pool.execute(
        "UPDATE post_history SET owner_decision = 'rejected', updated_at = now() WHERE id = $1",
        post_id,
    )


async def mark_published(post_id: str, gbp_post_id: str) -> None:
    pool = get_pool()
    await pool.execute(
        """
        UPDATE post_history
        SET gbp_post_id = $2, published_at = now(), updated_at = now()
        WHERE id = $1
        """,
        post_id,
        gbp_post_id,
    )
