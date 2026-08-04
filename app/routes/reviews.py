from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.db import get_pool
from app.services.reviews import list_unreplied_reviews, generate_suggested_reply, post_review_reply

router = APIRouter()

class ReviewReplyRequest(BaseModel):
    customer_id: str
    location_id: str
    review_id: str
    reply_text: str

class GenerateReplyRequest(BaseModel):
    review_text: str
    star_rating: int
    business_name: str
    tone: Optional[str] = "professional"

async def get_customer_location(customer_id: str):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT location_id, business_name FROM gbp_credentials gc JOIN customers c ON gc.customer_id = c.customer_id WHERE gc.customer_id = $1 LIMIT 1",
        customer_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Customer or location not found")
    return row["location_id"], row["business_name"]

@router.get("/{customer_id}")
async def get_reviews(customer_id: str):
    location_id, _ = await get_customer_location(customer_id)
    if location_id == "pending_location_discovery":
         return {"reviews": []}
         
    reviews = await list_unreplied_reviews(customer_id, location_id)
    return {"reviews": reviews}

@router.post("/generate-suggestion")
async def suggest_reply(req: GenerateReplyRequest):
    suggestion = await generate_suggested_reply(
        review_text=req.review_text,
        star_rating=req.star_rating,
        business_name=req.business_name,
        tone=req.tone
    )
    return {"suggestion": suggestion}

@router.post("/submit-reply")
async def submit_reply(req: ReviewReplyRequest):
    success = await post_review_reply(
        customer_id=req.customer_id,
        location_id=req.location_id,
        review_id=req.review_id,
        reply_text=req.reply_text
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to post reply to Google")
    return {"success": True}
