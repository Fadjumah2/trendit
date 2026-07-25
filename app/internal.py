"""
Internal-only route, called by the forked Node MCP server (googleAuth.ts)
instead of it reading a local token file. Protected by a shared secret
(INTERNAL_TOKEN) — this must never be exposed publicly or reused as a
customer-facing auth mechanism.

This is Option A from mcp_server/README.md: keep all credential
storage/encryption in this Python backend; the Node process just asks for
what it needs, per request, per customer/location.
"""
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.credentials.store import (
    get_credentials,
    get_credentials_by_location,
    update_refreshed_credentials,
    delete_credentials_by_location,
)

router = APIRouter(prefix="/internal")


def _check_internal_token(x_internal_token: str) -> None:
    if not settings.INTERNAL_TOKEN or x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="invalid internal token")


class RefreshCredentialsRequest(BaseModel):
    location_id: str
    access_token: str
    refresh_token: str
    token_expires_at: datetime
    scopes: str | None = None


@router.get("/gbp-credentials")
async def internal_get_credentials(
    location_id: str,
    customer_id: str | None = None,
    x_internal_token: str = Header(default=""),
):
    _check_internal_token(x_internal_token)

    if customer_id:
        creds = await get_credentials(customer_id, location_id)
    else:
        creds = await get_credentials_by_location(location_id)

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


@router.post("/gbp-credentials")
async def internal_post_credentials(
    payload: RefreshCredentialsRequest,
    x_internal_token: str = Header(default=""),
):
    _check_internal_token(x_internal_token)

    success = await update_refreshed_credentials(
        location_id=payload.location_id,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        token_expires_at=payload.token_expires_at,
        scopes=payload.scopes,
    )
    if not success:
        raise HTTPException(status_code=404, detail="no credentials found for this location")

    return {"status": "ok"}


@router.delete("/gbp-credentials")
async def internal_delete_credentials(
    location_id: str,
    x_internal_token: str = Header(default=""),
):
    _check_internal_token(x_internal_token)

    await delete_credentials_by_location(location_id)
    return {"status": "ok"}
