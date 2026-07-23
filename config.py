"""
Central config. Everything reads env vars from here rather than
scattering os.getenv() calls through the codebase.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.environ["DATABASE_URL"]

    # Credential encryption (Fernet key, see .env.example for how to generate)
    CREDENTIALS_ENCRYPTION_KEY: str = os.environ["CREDENTIALS_ENCRYPTION_KEY"]

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    # Google GBP OAuth
    GBP_OAUTH_CLIENT_ID: str = os.environ.get("GBP_OAUTH_CLIENT_ID", "")
    GBP_OAUTH_CLIENT_SECRET: str = os.environ.get("GBP_OAUTH_CLIENT_SECRET", "")

    # Gemini / ADK
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    APP_BASE_URL: str = os.environ.get("APP_BASE_URL", "http://localhost:8080")
    ENV: str = os.environ.get("ENV", "development")


settings = Settings()
