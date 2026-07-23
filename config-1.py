"""
Central config. Everything reads env vars from here rather than
scattering os.getenv() calls through the codebase.

Variable names below match what's actually already set in Render
(see conversation) rather than the earlier placeholder names.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.environ["DATABASE_URL"]

    # Credential encryption (Fernet key). NOT yet in your Render env vars —
    # generate one and add it before save_credentials()/get_credentials()
    # in app/credentials/store.py will work:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    CREDENTIALS_ENCRYPTION_KEY: str = os.environ["CREDENTIALS_ENCRYPTION_KEY"]

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
    TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "")
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    # Google OAuth app identity — shared across every customer's consent flow.
    # Used by the website's OAuth callback to exchange each customer's own
    # authorization code for THEIR OWN access/refresh token pair, which then
    # gets written to gbp_credentials (per customer_id/location_id).
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # DEV-ONLY: your own personal GBP refresh token from OAuth Playground.
    # This lets you call MCP tools against your own test business without
    # running the full website OAuth flow. NEVER read this for a real
    # customer's request — production credential lookups always go through
    # gbp_credentials via app/credentials/store.py, keyed by customer_id.
    DEV_GOOGLE_REFRESH_TOKEN: str = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    # Internal service-to-service auth: the forked Node MCP server calls
    # back into this backend (e.g. GET /internal/gbp-credentials) to fetch
    # a customer's decrypted token pair. This shared secret authenticates
    # that call — see mcp_server/README.md, Option A.
    INTERNAL_TOKEN: str = os.environ.get("INTERNAL_TOKEN", "")
    BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://localhost:8080")

    # Gemini / ADK
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("AGENT_MODEL", "gemini-2.0-flash")

    ENV: str = os.environ.get("ENV", "development")


settings = Settings()
