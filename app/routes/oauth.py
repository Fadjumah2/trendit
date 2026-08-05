from datetime import datetime, timedelta, timezone
import httpx
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.config import settings
from app.db import get_pool
from app.credentials.store import save_credentials
from app.services.notify import send_connection_confirmation
from app.services.onboarding import complete_onboarding_process
from app.services.generation import generate_post_draft

router = APIRouter(prefix="/oauth", tags=["OAuth"])

class CallbackBody(BaseModel):
    code: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = 3600
    email: str | None = None
    location_id: str | None = None
    business_name: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None

@router.post("/callback")
async def oauth_callback(body: CallbackBody):
    access_token = body.access_token
    refresh_token = body.refresh_token
    expires_in = body.expires_in
    scope = body.scope
    
    async with httpx.AsyncClient() as client:
        # 1. Exchange code if tokens not provided
        if body.code and not access_token:
            redirect_uri = body.redirect_uri or f"{settings.BACKEND_URL}/auth/callback"
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
            expires_in = tokens.get("expires_in", 3600)
            scope = tokens.get("scope")

        if not access_token:
            raise HTTPException(status_code=400, detail="Missing authorization code or access token")
            
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

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
        
        MOCK_LOCATION_ID = "accounts/mock123/locations/loc456"
        is_team = email in settings.TEAM_EMAILS

        if not location_id:
            # If mock mode is enabled and NOT a team email, go straight to mock
            if settings.ENABLE_MOCK_MODE and not is_team:
                print(f"DEBUG: Mock Mode active for {email}. Assigning {MOCK_LOCATION_ID}")
                location_id = MOCK_LOCATION_ID
            else:
                print(f"DEBUG: Starting discovery for email {email}")
                try:
                    # List accounts
                    accounts_resp = await client.get(
                        "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    print(f"DEBUG: Accounts API status: {accounts_resp.status_code}")
                    
                    # Handle 429 Resource Exhausted (Quota)
                    if accounts_resp.status_code == 429:
                        print(f"DEBUG: Quota exhausted for {email}")
                        if settings.ENABLE_MOCK_MODE:
                            print(f"DEBUG: Falling back to Mock Mode for team member {email}")
                            location_id = MOCK_LOCATION_ID
                        else:
                            location_id = "pending_location_discovery"
                    elif accounts_resp.status_code == 200:
                        accounts = accounts_resp.json().get("accounts", [])
                        print(f"DEBUG: Found {len(accounts)} accounts")
                        
                        for acc in accounts:
                            curr_acc_id = acc["name"]
                            print(f"DEBUG: Checking account: {curr_acc_id} ({acc.get('accountName', 'N/A')})")
                            
                            # List locations for this specific account
                            locations_resp = await client.get(
                                f"https://mybusinessbusinessinformation.googleapis.com/v1/{curr_acc_id}/locations?readMask=name,title",
                                headers={"Authorization": f"Bearer {access_token}"}
                            )
                            print(f"DEBUG: Locations API status for {curr_acc_id}: {locations_resp.status_code}")
                            
                            if locations_resp.status_code == 200:
                                locations = locations_resp.json().get("locations", [])
                                print(f"DEBUG: Found {len(locations)} locations in account {curr_acc_id}")
                                if locations:
                                    location_id = locations[0]["name"]
                                    account_id = curr_acc_id
                                    print(f"DEBUG: Selected location_id: {location_id}")
                                    break
                            elif locations_resp.status_code == 429 and settings.ENABLE_MOCK_MODE:
                                print(f"DEBUG: Quota exhausted during location list for {email}, using mock.")
                                location_id = MOCK_LOCATION_ID
                                break
                    else:
                        print(f"DEBUG: Accounts API Error: {accounts_resp.text}")
                        if settings.ENABLE_MOCK_MODE:
                            location_id = MOCK_LOCATION_ID
                except Exception as e:
                    print(f"DEBUG: Discovery exception for {email}: {e}")
                    if settings.ENABLE_MOCK_MODE:
                        location_id = MOCK_LOCATION_ID
        
        if not location_id:
            print(f"DEBUG: No locations found across any accounts for {email}")
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
        scopes=scope,
    )

    # 3b. Ensure a content profile exists (auto-onboarding if no answers provided yet)
    # This allows skipping the pre-connection questions while still having a working agent.
    if location_id != "pending_location_discovery":
        try:
            from app.agent.content_profile import get_content_profile
            existing_profile = await get_content_profile(customer_id, location_id)
            if not existing_profile:
                print(f"DEBUG: Auto-generating baseline profile for {email}")
                # We do NOT await this in the main thread if we want it to be ultra-fast, 
                # but complete_onboarding_process is already async. 
                # Let's wrap the whole thing in a background task to be safe against timeouts.
                async def background_onboarding():
                    try:
                        await complete_onboarding_process(customer_id, location_id, {})
                        # Trigger first draft generation in background
                        await generate_post_draft(customer_id, location_id, post_type="standard")
                    except Exception as e:
                        print(f"DEBUG: Background onboarding/drafting failed: {e}")
                
                asyncio.create_task(background_onboarding())
        except Exception as e:
            print(f"DEBUG: Failed to check/trigger auto-onboarding: {e}")

    # 4. Fire the confirmation (non-blocking so email failure doesn't break the flow)
    asyncio.create_task(send_connection_confirmation(customer_id, location_id))

    print(f"DEBUG: OAuth callback successful for {email}. Returning customer_id: {customer_id}")
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

    # This is the trigger: once the content profile exists, kick off the
    # first draft so the owner gets something to approve without any
    # manual step. Wrapped so a generation hiccup doesn't fail onboarding
    # itself (the profile is already saved at this point).
    if body.location_id != "pending_location_discovery":
        try:
            await generate_post_draft(
                customer_id=body.customer_id,
                location_id=body.location_id,
                post_type="standard",
            )
        except Exception as e:
            print(f"First draft generation failed for {body.customer_id}: {e}")
    else:
        print(f"Skipping first draft generation for {body.customer_id} as location is pending discovery.")

    return {"status": "profile_created", "profile": profile}
