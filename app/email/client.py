"""
Email client using Resend API.
"""
import httpx
import logging
from app.config import settings

# Basic logging setup
logger = logging.getLogger(__name__)

async def send_email(to: str, subject: str, html: str) -> dict:
    if not settings.RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY is not set in environment variables.")
        raise RuntimeError("RESEND_API_KEY is not set")
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Ensure 'from' address is using the verified domain
    from_email = settings.EMAIL_FROM
    
    payload = {
        "from": from_email,
        "to": to,
        "subject": subject,
        "html": html,
    }
    
    print(f"INFO: Sending email from '{from_email}' to '{to}' with subject: '{subject}'")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            
            if resp.status_code not in (200, 201):
                print(f"ERROR: Resend API error ({resp.status_code}): {resp.text}")
                resp.raise_for_status()
                
            result = resp.json()
            print(f"INFO: Email sent successfully. Resend ID: {result.get('id')}")
            return result
    except Exception as e:
        print(f"ERROR: Failed to send email to {to}: {str(e)}")
        raise
