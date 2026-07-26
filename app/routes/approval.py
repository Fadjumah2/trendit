"""
Routes for email-based post approval.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db import get_pool
from app.services.post_history import mark_approved, mark_skipped
from app.services.publish import publish_post
from app.email.templates import decision_result_page

router = APIRouter()

@router.get("/approve/{post_id}", response_class=HTMLResponse)
async def approve_post(post_id: str):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT owner_decision FROM post_history WHERE id = $1",
        post_id
    )
    
    if row is None:
        return HTMLResponse(content=decision_result_page("Draft not found."), status_code=404)
        
    owner_decision = row["owner_decision"]
    if owner_decision != "pending":
        return HTMLResponse(content=decision_result_page(f"This draft was already {owner_decision}."))

    await mark_approved(post_id)
    try:
        result = await publish_post(post_id)
        gbp_post_id = result.get("gbp_post_id", "published")
        return HTMLResponse(content=decision_result_page(f"Approved and published! Reference: {gbp_post_id}"))
    except Exception as e:
        # If publish fails, we already marked it approved in our DB. 
        # In a real app, we might want to handle retries or a "failed" state.
        return HTMLResponse(content=decision_result_page(f"Approved, but failed to publish to GBP: {str(e)}"), status_code=500)

@router.get("/reject/{post_id}", response_class=HTMLResponse)
async def reject_post(post_id: str):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT owner_decision FROM post_history WHERE id = $1",
        post_id
    )
    
    if row is None:
        return HTMLResponse(content=decision_result_page("Draft not found."), status_code=404)
        
    owner_decision = row["owner_decision"]
    if owner_decision != "pending":
        return HTMLResponse(content=decision_result_page(f"This draft was already {owner_decision}."))

    await mark_skipped(post_id)
    return HTMLResponse(content=decision_result_page("Draft rejected and will not be published."))
