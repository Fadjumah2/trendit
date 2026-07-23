"""
Final publish step: takes an approved post_history row and calls the MCP
server's create_local_post tool via the ADK agent's toolset. This is the
only place in the codebase that should ever result in a live GBP post being
created — approval in webhook.py must happen first.
"""
from app.db import get_pool
from app.services.post_history import mark_published


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

    # TODO: call the MCP create_local_post tool here, e.g. via the ADK
    # agent's toolset or a direct MCP client call, passing customer_id/
    # location_id so the forked server resolves the right credentials:
    #
    #   gbp_post_id = await mcp_toolset.call_tool(
    #       "create_local_post",
    #       customer_id=customer_id,
    #       location_id=location_id,
    #       post_type=post_type,
    #       **content,
    #   )
    #
    # Left as a stub until the MCP fork's tool signatures are finalized
    # (see mcp_server/README.md, point 3 — customer_id/location_id threading).
    gbp_post_id = "STUB-" + post_id[:8]

    await mark_published(post_id, gbp_post_id)

    return {"post_type": post_type, "gbp_post_id": gbp_post_id}
