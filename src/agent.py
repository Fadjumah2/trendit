import asyncio
import json
import logging
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# v1: only expose Local Posts tools.
V1_ALLOWED_TOOLS = [
    "get_local_posts",
    "create_local_post",
    "update_local_post",
    "delete_local_post",
]

def build_system_prompt() -> str:
    """Builds a professional GBP assistant system prompt."""
    return """You are a Google Business Profile (GBP) post-writing assistant.
Your goal is to help businesses manage their local posts efficiently.

You have access to the following tools:
- get_local_posts: Fetch existing posts.
- create_local_post: Draft and publish a new post.
- update_local_post: Edit an existing post.
- delete_local_post: Remove a post.
- list_locations: Find business locations.

Follow these rules:
1. Professional Tone: Always be professional and helpful.
2. Character Limits: Titles should be under 58 characters. Descriptions should be concise but informative.
3. Forbidden Content: Do not include phone numbers, emails, or URLs in the post body. Use the Call to Action (CTA) field for links.
4. Approval: Only call create_local_post or update_local_post after the user has approved the draft content.

Output format for drafts:
Always show the user the drafted Title, Body, and CTA before publishing.
"""

async def get_agent_async():
    """Creates an ADK Agent equipped with GBP tools from the MCP Server."""
    
    # Connect to the MCP server using stdio
    # We use 'python3' and the path to mcp_server.py
    connection_params = StdioServerParameters(
        command="python3",
        args=["src/mcp_server.py"],
        env={"PYTHONPATH": "."}
    )
    
    tools, exit_stack = await MCPToolset.from_server(connection_params=connection_params)
    
    # Filter tools to only include allowed ones if necessary
    filtered_tools = [t for t in tools if t.name in V1_ALLOWED_TOOLS or t.name == "list_locations"]
    
    logger.info(f"Fetched {len(filtered_tools)} tools from MCP server.")
    
    agent = LlmAgent(
        model=settings.GEMINI_MODEL,
        name="gbp_assistant",
        instruction=build_system_prompt(),
        tools=filtered_tools,
    )
    
    return agent, exit_stack

async def run_agent_task(query: str):
    agent, exit_stack = await get_agent_async()
    runner = Runner()
    
    print(f"Executing task: {query}")
    try:
        response = await runner.run(agent, query)
        print(f"\nAgent Response:\n{response.text}")
    finally:
        await exit_stack.aclose()

def main():
    print("Trendit GBP Agent System Ready.")
    query = "List my locations and show me the latest posts for the Coffee Shop."
    asyncio.run(run_agent_task(query))

if __name__ == "__main__":
    main()
