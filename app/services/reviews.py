import os
import json
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from app.config import settings
from app.db import get_pool

_MCP_SERVER_DIR = Path(__file__).parents[2] / "mcp_server"

def _get_mcp_params(is_mock: bool = False):
    mcp_env = os.environ.copy()
    mcp_env["NODE_ENV"] = "production"
    mcp_env["TRANSPORT_MODE"] = "stdio"
    if is_mock:
        mcp_env["ENABLE_MOCK_MODE"] = "true"
    
    return StdioServerParameters(
        command="node",
        args=["build/index.js"],
        cwd=str(_MCP_SERVER_DIR),
        env=mcp_env
    )

async def list_unreplied_reviews(customer_id: str, location_id: str) -> list:
    """
    Fetch unreplied reviews for a specific location using the MCP server.
    """
    is_mock = location_id.startswith("accounts/mock")
    params = _get_mcp_params(is_mock=is_mock)
    
    # Format location name correctly: if it already has accounts/ or locations/ don't prefix
    location_name = location_id
    if not (location_name.startswith("locations/") or location_name.startswith("accounts/")):
        location_name = f"locations/{location_id}"

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                name="get_unreplied_reviews",
                arguments={
                    "locationName": location_name,
                    "pageSize": 20
                },
            )
            
            # The MCP server returns reviews in result.structuredContent.reviews
            if hasattr(result, "structuredContent") and result.structuredContent:
                return result.structuredContent.get("reviews", [])
            
            return []

async def post_review_reply(customer_id: str, location_id: str, review_id: str, reply_text: str) -> bool:
    """
    Post a reply to a review using the MCP server.
    """
    is_mock = location_id.startswith("accounts/mock")
    params = _get_mcp_params(is_mock=is_mock)
    
    location_name = location_id
    if not (location_name.startswith("locations/") or location_name.startswith("accounts/")):
        location_name = f"locations/{location_id}"

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                name="post_reply",
                arguments={
                    "locationName": location_name,
                    "reviewId": review_id,
                    "comment": reply_text
                },
            )
            
            # Check if result is success
            return not getattr(result, "isError", False)

async def generate_suggested_reply(review_text: str, star_rating: int, business_name: str, tone: str = "professional") -> str:
    """
    Generate a suggested reply using Gemini.
    """
    from google import genai
    from app.config import settings
    
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    prompt = f"""
    You are writing a professional and brand-consistent response to a customer review for {business_name}.

    Review Details:
    - Star Rating: {star_rating}/5
    - Review Text: "{review_text}"
    - Desired Tone: {tone}

    Guidelines:
    1. Be sincere, polite, and {tone}.
    2. {'Thank them for their positive feedback' if star_rating >= 4 else 'Address their concerns empathetically and professionally'}.
    3. Reference specific details from the review if applicable.
    4. Keep it concise (under 100 words).
    5. {'Encourage them to visit again' if star_rating >= 4 else 'Offer to resolve any issues offline if appropriate'}.

    Write the response text only. No greetings like 'Here is the response' - just the reply content.
    """
    
async def auto_draft_review_replies(customer_id: str, location_id: str) -> list:
    """
    1. Scan GBP for unreplied reviews.
    2. Check DB to see which ones we haven't drafted yet.
    3. Generate and save drafts for new unreplied reviews.
    """
    # 1. Fetch unreplied reviews from GBP
    unreplied = await list_unreplied_reviews(customer_id, location_id)
    if not unreplied:
        return []

    pool = get_pool()
    drafted_ids = []

    # Get business name for Gemini context
    biz_row = await pool.fetchrow("SELECT business_name FROM customers WHERE customer_id = $1", customer_id)
    business_name = biz_row["business_name"] if biz_row else "your business"

    for review in unreplied:
        review_id = review["reviewId"]
        
        # Check if we already have a record for this review
        existing = await pool.fetchrow(
            "SELECT id FROM review_reply_history WHERE location_id = $1 AND review_id = $2",
            location_id, review_id
        )
        if existing:
            continue

        # Generate draft
        review_text = review.get("comment", "")
        star_rating = 0
        rating_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
        star_rating = rating_map.get(review.get("starRating", "FIVE"), 5)

        try:
            draft_text = await generate_suggested_reply(
                review_text=review_text,
                star_rating=star_rating,
                business_name=business_name
            )

            # Save to history
            res = await pool.fetchrow(
                """
                INSERT INTO review_reply_history 
                (customer_id, location_id, review_id, reviewer_name, review_text, star_rating, draft_reply)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                customer_id, location_id, review_id, 
                review.get("reviewer", {}).get("displayName"),
                review_text, star_rating, draft_text
            )
            drafted_ids.append(str(res["id"]))
            
            # Send notification email (to be implemented)
            from app.services.notify import send_review_reply_for_approval
            await send_review_reply_for_approval(str(res["id"]))

        except Exception as e:
            print(f"Failed to draft reply for review {review_id}: {e}")

    return drafted_ids

