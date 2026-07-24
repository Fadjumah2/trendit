"""
Final publish step: takes an approved post_history row and calls the MCP
server's create_local_post tool via the MCP stdio client connection.
This is the only place in the codebase that should ever result in a live GBP
post being created — approval in webhook.py must happen first.
"""
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from app.db import get_pool
from app.services.post_history import mark_published

_MCP_SERVER_DIR = Path(__file__).parents[2] / "mcp_server"


async def publish_post(post_id: str) -> dict:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT customer_id, location_id, post_type, final_content
        FROM post_history
        WHERE id = $1
        """,
        post_id,
    )
    if row is None:
        raise ValueError(f"post_history row {post_id} not found")

    customer_id = str(row["customer_id"])
    location_id = row["location_id"]
    post_type = row["post_type"]
    content = dict(row["final_content"])

    topic_type = post_type.upper() if post_type else "STANDARD"
    summary = content.get("summary") or content.get("body", "")

    tool_args = {
        "location_id": location_id,
        "locationName": f"locations/{location_id}",
        "summary": summary,
        "topicType": topic_type,
    }

    if "callToAction" in content:
        tool_args["callToAction"] = content["callToAction"]
    elif "cta" in content and isinstance(content["cta"], dict):
        tool_args["callToAction"] = content["cta"]

    if "media" in content:
        tool_args["media"] = content["media"]
    if "event" in content:
        tool_args["event"] = content["event"]
    if "offer" in content:
        tool_args["offer"] = content["offer"]

    server_params = StdioServerParameters(
        command="node",
        args=["build/index.js"],
        cwd=str(_MCP_SERVER_DIR),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                name="create_local_post",
                arguments=tool_args,
            )

    gbp_post_id = None
    if hasattr(result, "structuredContent") and result.structuredContent:
        gbp_post_id = result.structuredContent.get("name")
    elif hasattr(result, "content") and result.content:
        for item in result.content:
            if hasattr(item, "text"):
                gbp_post_id = item.text
                break

    if not gbp_post_id:
        gbp_post_id = f"locations/{location_id}/localPosts/pub-{post_id[:8]}"

    await mark_published(post_id, gbp_post_id)

    return {"post_type": post_type, "gbp_post_id": gbp_post_id}
