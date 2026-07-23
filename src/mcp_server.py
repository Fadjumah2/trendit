from mcp.server.fastmcp import FastMCP
from business_logic import GBPManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Trendit GBP Server")
gbp = GBPManager()

@mcp.tool()
def get_local_posts(location_id: str) -> str:
    """Fetch all local posts for a specific Google Business Profile location."""
    logger.info(f"Fetching posts for location: {location_id}")
    posts = gbp.get_local_posts(f"locations/{location_id}")
    return str(posts)

@mcp.tool()
def create_local_post(location_id: str, summary: str, call_to_action_type: str = "LEARN_MORE") -> str:
    """Create a new local post for a Google Business Profile location."""
    logger.info(f"Creating post for location: {location_id}")
    post_data = {
        "summary": summary,
        "callToAction": {"actionType": call_to_action_type}
    }
    result = gbp.create_local_post(f"locations/{location_id}", post_data)
    return f"Successfully created post: {result.get('name')}"

@mcp.tool()
def update_local_post(post_id: str, summary: str) -> str:
    """Update an existing local post."""
    logger.info(f"Updating post: {post_id}")
    post_data = {"summary": summary}
    result = gbp.update_local_post(post_id, post_data)
    return f"Successfully updated post: {result.get('name')}"

@mcp.tool()
def delete_local_post(post_id: str) -> str:
    """Delete a local post."""
    logger.info(f"Deleting post: {post_id}")
    success = gbp.delete_local_post(post_id)
    return "Successfully deleted post." if success else "Failed to delete post."

@mcp.tool()
def list_locations() -> str:
    """List all Google Business Profile locations for the authenticated account."""
    locations = gbp.list_locations()
    return str(locations)

if __name__ == "__main__":
    mcp.run()
