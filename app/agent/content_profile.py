"""
Reads/writes the business_content_profile — the compact, reusable JSON
distilled once at signup.
"""
import json
from app.db import get_pool

async def get_content_profile(customer_id: str, location_id: str) -> dict | None:
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
    if not row:
        return None
        
    profile = row["profile_json"]
    if isinstance(profile, str):
        return json.loads(profile)
    return dict(profile)

async def save_content_profile(
    customer_id: str,
    location_id: str,
    profile_json: dict,
    source_intake_json: dict | None = None,
) -> None:
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
        json.dumps(profile_json) if isinstance(profile_json, dict) else profile_json,
        json.dumps(source_intake_json) if isinstance(source_intake_json, dict) else source_intake_json,
    )

async def get_recent_approved_posts(customer_id: str, location_id: str, limit: int = 5) -> list[dict]:
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
    results = []
    for r in rows:
        content = r["final_content"]
        if isinstance(content, str):
            results.append(json.loads(content))
        else:
            results.append(dict(content))
    return results
