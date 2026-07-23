"""
Postgres-backed OAuth credential storage for GBP tokens.

THIS is the piece that replaces jmdurant/gbp-mcp-server's stock file-based
token storage. In the forked MCP server, find wherever it currently does
something like:

    read tokens from ./credentials.json
    write tokens to ./credentials.json

...and swap those calls for get_credentials() / save_credentials() below,
passing in (customer_id, location_id) resolved from the incoming request
instead of always touching one global file.

Tokens are encrypted at the app layer with Fernet (symmetric encryption)
before they ever touch the database — Postgres just stores opaque bytes.
"""
from datetime import datetime, timezone
from dataclasses import dataclass

from cryptography.fernet import Fernet

from app.config import settings
from app.db import get_pool

_fernet = Fernet(settings.CREDENTIALS_ENCRYPTION_KEY.encode())


@dataclass
class GbpCredentials:
    customer_id: str
    location_id: str
    account_id: str | None
    access_token: str
    refresh_token: str
    token_expires_at: datetime
    scopes: str | None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.token_expires_at


def _encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()


async def get_credentials(customer_id: str, location_id: str) -> GbpCredentials | None:
    """Look up + decrypt tokens for one customer/location. Called by the MCP
    server before every GBP API call it makes on that customer's behalf."""
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT customer_id, location_id, account_id, access_token,
               refresh_token, token_expires_at, scopes
        FROM gbp_credentials
        WHERE customer_id = $1 AND location_id = $2
        """,
        customer_id,
        location_id,
    )
    if row is None:
        return None

    return GbpCredentials(
        customer_id=str(row["customer_id"]),
        location_id=row["location_id"],
        account_id=row["account_id"],
        access_token=_decrypt(row["access_token"]),
        refresh_token=_decrypt(row["refresh_token"]),
        token_expires_at=row["token_expires_at"],
        scopes=row["scopes"],
    )


async def save_credentials(
    customer_id: str,
    location_id: str,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
    account_id: str | None = None,
    scopes: str | None = None,
) -> None:
    """Upsert tokens. Called once after the website's OAuth callback, and
    again every time the MCP server refreshes an access token."""
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO gbp_credentials
            (customer_id, location_id, account_id, access_token,
             refresh_token, token_expires_at, scopes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (customer_id, location_id)
        DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            token_expires_at = EXCLUDED.token_expires_at,
            account_id = COALESCE(EXCLUDED.account_id, gbp_credentials.account_id),
            scopes = COALESCE(EXCLUDED.scopes, gbp_credentials.scopes),
            updated_at = now()
        """,
        customer_id,
        location_id,
        account_id,
        _encrypt(access_token),
        _encrypt(refresh_token),
        token_expires_at,
        scopes,
    )


async def delete_credentials(customer_id: str, location_id: str) -> None:
    """Used if a customer disconnects their GBP profile."""
    pool = get_pool()
    await pool.execute(
        "DELETE FROM gbp_credentials WHERE customer_id = $1 AND location_id = $2",
        customer_id,
        location_id,
    )
