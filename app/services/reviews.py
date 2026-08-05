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
    
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt
    )
    
    return response.text.strip()
