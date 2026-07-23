import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    # Default location for demo
    DEFAULT_LOCATION_ID: str = "123"

settings = Settings()
