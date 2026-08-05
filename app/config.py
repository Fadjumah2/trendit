"""
Central config. Everything reads env vars from here rather than
scattering os.getenv() calls through the codebase.
"""
import os
from dotenv import load_dotenv

# Load from the parent directory if running from app/ or similar
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "postgresql://localhost/trendit")

    # Credential encryption (Fernet key).
    # If missing, we use a dummy key for local testing to prevent crashes.
    # Production MUST set this.
    CREDENTIALS_ENCRYPTION_KEY: str = os.environ.get(
        "CREDENTIALS_ENCRYPTION_KEY", 
        "dzhxUjosRo_kJL-5od8uhrgowOtMWZUyG8NaFUUJOHA=" 
    ).strip()

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_TOKEN", "").strip()
    TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "").strip()
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Internal service-to-service auth
    INTERNAL_TOKEN: str = os.environ.get("INTERNAL_TOKEN", "")
    BACKEND_URL: str = os.environ.get(
        "BACKEND_URL", 
        "https://trendit-4ocu.onrender.com" if os.environ.get("RENDER") else "http://localhost:8080"
    )

    # Gemini / ADK
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("AGENT_MODEL", "gemini-2.0-flash")

    # Email (Resend)
    RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")
    # Verified domain: forms.trendexhub.com
    EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "Trendit <notifications@forms.trendexhub.com>")

    ENV: str = os.environ.get("ENV", "production" if os.environ.get("RENDER") else "development")
    ENABLE_MOCK_MODE: bool = os.environ.get("ENABLE_MOCK_MODE", "true").lower() == "true"
    TEAM_EMAILS: list[str] = ["eritageentcare@gmail.com", "trendexhub@gmail.com"]


settings = Settings()
