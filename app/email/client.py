"""
Email client using Resend API.
"""
import httpx
from app.config import settings

async def send_email(to: str, subject: str, html: str) -> dict:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set")
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
