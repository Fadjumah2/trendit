from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db import get_pool

router = APIRouter()

class UserProfileResponse(BaseModel):
    customer_id: str
    email: str
    business_name: Optional[str] = None
    location_id: Optional[str] = None
    onboarding_status: str  # 'complete', 'pending_discovery', 'initializing'

@router.get("/profile/{customer_id}")
async def get_user_profile(customer_id: str):
    pool = get_pool()
    
    # Fetch customer and credentials
    row = await pool.fetchrow(
        """
        SELECT c.email, c.business_name, gc.location_id
        FROM customers c
        LEFT JOIN gbp_credentials gc ON c.customer_id = gc.customer_id
        WHERE c.customer_id = $1
        """,
        customer_id
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check onboarding status by seeing if a profile exists
    profile_row = await pool.fetchrow(
        "SELECT profile_json FROM business_content_profiles WHERE customer_id = $1",
        customer_id
    )
    
    status = "initializing"
    profile_data = None
    if profile_row:
        status = "complete"
        profile_data = profile_row["profile_json"]
    elif row["location_id"] == "pending_location_discovery":
        status = "pending_discovery"
        
    return {
        "customer_id": customer_id,
        "email": row["email"],
        "business_name": row["business_name"] or "Unknown Business",
        "location_id": row["location_id"],
        "onboarding_status": status,
        "profile": profile_data
    }
