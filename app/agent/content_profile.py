"""
Reads/writes the business_content_profile — the compact, reusable JSON
distilled once at signup (tone, core services, content pillars, example
phrasing, keywords) from the onboarding intake + pulled GBP data.

This is intentionally plain Postgres, not ADK MemoryService/RAG — the data
is structured and small enough that semantic search is unnecessary. Revisit
only if "have I written about X before" fuzzy search becomes a real need
(see Phase 7 in the roadmap).
"""
from app.db import get_pool


async def get_content_profile(customer_id: str, location_id: str) -> dict | None:
    """Fetched by the backend's context-assembly step before every agent
    call — injected into the system prompt so the agent never re-derives
    'what kind of business is this' from scratch."""
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT profile_json
        FROM business_content_profiles
        WHERE customer_id = $1 AND location_id = $2
        """,
        customer_id,
        location_id,
    )
    return dict(row["profile_json"]) if row else None


async def save_content_profile(
    customer_id: str,
    location_id: str,
    profile_json: dict,
    source_intake_json: dict | None = None,
) -> None:
    """Called once after the signup LLM call, and again whenever the profile
    is refreshed (periodically, or after repeated owner edits)."""
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO business_content_profiles
            (customer_id, location_id, profile_json, source_intake_json)
        VALUES ($1, $2, $3::jsonb, $4::jsonb)
        ON CONFLICT (customer_id, location_id)
        DO UPDATE SET
            profile_json = EXCLUDED.profile_json,
            source_intake_json = COALESCE(EXCLUDED.source_intake_json, business_content_profiles.source_intake_json),
            last_refreshed_at = now()
        """,
        customer_id,
        location_id,
        profile_json,
        source_intake_json,
    )


async def get_recent_approved_posts(customer_id: str, location_id: str, limit: int = 5) -> list[dict]:
    """Feeds the feedback loop — a few of the owner's own approved posts,
    used as few-shot examples on future drafts."""
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT final_content
        FROM post_history
        WHERE customer_id = $1 AND location_id = $2
          AND owner_decision = 'approved'
          AND final_content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT $3
        """,
        customer_id,
        location_id,
        limit,
    )
    return [dict(r["final_content"]) for r in rows]
