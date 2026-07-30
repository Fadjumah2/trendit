"""
Internal-only route, called by the forked Node MCP server (googleAuth.ts)
instead of it reading a local token file. Protected by a shared secret
(INTERNAL_TOKEN) — this must never be exposed publicly or reused as a
customer-facing auth mechanism.

This is Option A from mcp_server/README.md: keep all credential
storage/encryption in this Python backend; the Node process just asks for
what it needs, per request, per customer/location.
"""
from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.credentials.store import get_credentials
from app.db import get_pool
from app.services.generation import generate_post_draft

router = APIRouter(prefix="/internal")


def _check_internal_token(x_internal_token: str) -> None:
    if not settings.INTERNAL_TOKEN or x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="invalid internal token")


@router.post("/generate-drafts")
async def internal_generate_drafts(x_internal_token: str = Header(default="")):
    """
    Recurring draft-generation trigger. Meant to be called once every 24
    hours by an external scheduler (e.g. a GitHub Actions cron workflow)
    rather than a Render Cron Job, since Cron Jobs aren't available on
    Render's free instance type.

    For every connected customer/location with a saved content profile
    that does NOT already have a pending (un-decided) draft, generates a
    new "standard" post and emails it for approval.
    """
    _check_internal_token(x_internal_token)

    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT DISTINCT gc.customer_id, gc.location_id
        FROM gbp_credentials gc
        JOIN business_content_profiles bcp
          ON bcp.customer_id = gc.customer_id
         AND bcp.location_id = gc.location_id
        WHERE NOT EXISTS (
            SELECT 1 FROM post_history ph
            WHERE ph.customer_id = gc.customer_id
              AND ph.location_id = gc.location_id
              AND ph.owner_decision = 'pending'
        )
        """
    )

    results = []
    for row in rows:
        customer_id = str(row["customer_id"])
        location_id = row["location_id"]
        try:
            post_id = await generate_post_draft(customer_id, location_id, "standard")
            results.append({"customer_id": customer_id, "location_id": location_id, "post_id": post_id, "ok": True})
        except Exception as e:
            # One customer's failure shouldn't stop the batch.
            results.append({"customer_id": customer_id, "location_id": location_id, "error": str(e), "ok": False})

    return {
        "checked": len(rows),
        "succeeded": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }


@router.get("/gbp-credentials")
async def internal_get_credentials(
    customer_id: str,
    location_id: str,
    x_internal_token: str = Header(default=""),
):
    _check_internal_token(x_internal_token)

    creds = await get_credentials(customer_id, location_id)
    if creds is None:
        raise HTTPException(status_code=404, detail="no credentials for this customer/location")

    # Decrypted tokens leave this process only over this internal channel,
    # authenticated by INTERNAL_TOKEN, ideally over a private network path
    # (Render internal networking) rather than the public internet.
    return {
        "access_token": creds.access_token,
        "refresh_token": creds.refresh_token,
        "token_expires_at": creds.token_expires_at.isoformat(),
        "account_id": creds.account_id,
        "scopes": creds.scopes,
    }
