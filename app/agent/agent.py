"""
ADK LlmAgent (Gemini) orchestrator.
"""
import json
import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

from app.config import settings

_RULES_PATH = Path(__file__).parent / "policy_rules.json"
_POLICY_RULES = json.loads(_RULES_PATH.read_text())

V1_ALLOWED_TOOLS = [
    "get_local_posts",
    "create_local_post",
    "update_local_post",
    "delete_local_post",
]

def _policy_slice_for(post_type: str) -> dict:
    return {
        "common": _POLICY_RULES["common"],
        post_type: _POLICY_RULES.get(post_type, {}),
    }

def build_system_prompt(post_type: str, content_profile: dict, few_shot_posts: list[dict]) -> str:
    policy_slice = _policy_slice_for(post_type)
    few_shot_block = ""
    if few_shot_posts:
        examples = "\n".join(f"- {json.dumps(p)}" for p in few_shot_posts)
        few_shot_block = f"\nExamples of this owner's previously approved posts:\n{examples}\n"

    return f"""You are a Google Business Profile post-writing assistant for a small business.

Business content profile:
{json.dumps(content_profile, indent=2)}
{few_shot_block}
You are drafting a "{post_type}" post. Follow these policy rules exactly:
{json.dumps(policy_slice, indent=2)}

Output ONLY the post content as JSON. Do not include phone numbers or emails in the body.
"""

def build_agent(post_type: str, content_profile: dict, few_shot_posts: list[dict], tools: list = None) -> LlmAgent:
    return LlmAgent(
        model=settings.GEMINI_MODEL,
        name="gbp_post_writer",
        instruction=build_system_prompt(post_type, content_profile, few_shot_posts),
        tools=tools or [],
    )

def get_mcp_server_params():
    # Pass necessary env vars to the MCP subprocess
    mcp_env = os.environ.copy()
    mcp_env["NODE_ENV"] = "production"
    mcp_env["TRANSPORT_MODE"] = "stdio"
    
    # Use absolute path for robustness in Docker/Render
    mcp_dir = Path(__file__).parents[2] / "mcp_server"
    
    return StdioServerParameters(
        command="node",
        args=["build/index.js"],
        cwd=str(mcp_dir),
        env=mcp_env
    )
