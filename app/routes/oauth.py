from datetime import datetime, timedelta, timezone
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.db import get_pool
from app.credentials.store import save_credentials
from app.services.notify import send_connection_confirmation
from app.services.onboarding import complete_onboarding_process

router = APIRouter(prefix="/oauth", tags=["OAuth"])

class CallbackBody(BaseModel):
    code: str
    email: str | None = None
    location_id: str | None = None
    business_name: str | None = None
    redirect_uri: str | None = None

@router.post("/callback")
async def oauth_callback(body: CallbackBody):
    # 1. Exchange code for tokens
    redirect_uri = body.redirect_uri or f"{settings.BACKEND_URL}/auth/callback"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Google token exchange failed: {resp.text}")

        tokens = resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh_token returned — check prompt=consent&access_type=offline on the auth URL")
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))

        # 1b. Fetch User Info if email is missing
        email = body.email
        if not email:
            user_info_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_info_resp.status_code == 200:
                email = user_info_resp.json().get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required but could not be fetched from Google")

        # 1c. Fetch location_id if missing
        location_id = body.location_id
        account_id = None
        if not location_id:
            # List accounts
            accounts_resp = await client.get(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if accounts_resp.status_code == 200:
                accounts = accounts_resp.json().get("accounts", [])
                if accounts:
                    account_id = accounts[0]["name"] # e.g. "accounts/123"
                    # List locations
                    locations_resp = await client.get(
                        f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_id}/locations?readMask=name,title",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if locations_resp.status_code == 200:
                        locations = locations_resp.json().get("locations", [])
                        if locations:
                            location_id = locations[0]["name"] # e.g. "locations/456"
        
        if not location_id:
            # Fallback for dev/test if no locations found
            location_id = "pending_location_discovery"

    # 2. Find-or-create the customer row
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO customers (email, business_name)
        VALUES ($1, $2)
        ON CONFLICT (email) DO UPDATE SET 
            business_name = COALESCE(EXCLUDED.business_name, customers.business_name),
            updated_at = now()
        RETURNING customer_id
        """,
        email,
        body.business_name,
    )
    customer_id = str(row["customer_id"])

    # 3. Save credentials
    await save_credentials(
        customer_id=customer_id,
        location_id=location_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=expires_at,
        account_id=account_id,
        scopes=tokens.get("scope"),
    )

    # 4. Fire the confirmation
    await send_connection_confirmation(customer_id, location_id)

    return {"customer_id": customer_id, "status": "connected", "location_id": location_id}

class OnboardingCompleteBody(BaseModel):
    customer_id: str
    location_id: str
    answers: dict

@router.post("/onboarding/complete")
async def onboarding_complete(body: OnboardingCompleteBody):
    profile = await complete_onboarding_process(
        customer_id=body.customer_id,
        location_id=body.location_id,
        source_intake=body.answers
    )
    return {"status": "profile_created", "profile": profile}
