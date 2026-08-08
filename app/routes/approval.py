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
        # NOTE: In the redefined workflow, approval will only set status='approved' 
        # and queue the post for the next scheduled publish window (6:00 AM daily).
        # Immediate publishing is retired.
        result = await publish_post(post_id)
        gbp_post_id = result.get("gbp_post_id", "published")
        return HTMLResponse(content=decision_result_page(f"Approved and queued for publish! Reference: {gbp_post_id}"))
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
    return HTMLResponse(content=decision_result_page("Draft rejected. No post was published."))

@router.get("/approve-review/{reply_id}", response_class=HTMLResponse)
async def approve_review_reply(reply_id: str):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT owner_decision, customer_id, location_id, review_id, draft_reply FROM review_reply_history WHERE id = $1",
        reply_id
    )
    
    if row is None:
        return HTMLResponse(content=decision_result_page("Reply not found."), status_code=404)
        
    if row["owner_decision"] != "pending":
        return HTMLResponse(content=decision_result_page(f"This reply was already {row['owner_decision']}."))

    # Update DB
    await pool.execute("UPDATE review_reply_history SET owner_decision = 'approved' WHERE id = $1", reply_id)
    
    try:
        from app.services.reviews import post_review_reply
        success = await post_review_reply(
            customer_id=str(row["customer_id"]),
            location_id=row["location_id"],
            review_id=row["review_id"],
            reply_text=row["draft_reply"]
        )
        if success:
            await pool.execute("UPDATE review_reply_history SET published_at = now() WHERE id = $1", reply_id)
            return HTMLResponse(content=decision_result_page("Reply approved and posted to Google!"))
        else:
            return HTMLResponse(content=decision_result_page("Reply approved, but failed to post to Google."), status_code=500)
    except Exception as e:
        return HTMLResponse(content=decision_result_page(f"Error posting reply: {str(e)}"), status_code=500)

@router.get("/reject-review/{reply_id}", response_class=HTMLResponse)
async def reject_review_reply(reply_id: str):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT owner_decision FROM review_reply_history WHERE id = $1",
        reply_id
    )
    
    if row is None:
        return HTMLResponse(content=decision_result_page("Reply not found."), status_code=404)
        
    if row["owner_decision"] != "pending":
        return HTMLResponse(content=decision_result_page(f"This reply was already {row['owner_decision']}."))

    await pool.execute("UPDATE review_reply_history SET owner_decision = 'rejected' WHERE id = $1", reply_id)
    return HTMLResponse(content=decision_result_page("Reply rejected and will not be posted."))

