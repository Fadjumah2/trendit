"""
ADK LlmAgent (Gemini) orchestrator, wired to the forked GBP MCP server via
McpToolset — filtered down to only the 4 Local Posts tools for v1.

NOTE: exact McpToolset / MCP connection params depend on how the forked
server is exposed (stdio subprocess vs. local HTTP). Check /mcp_server/README.md
in this repo — this file assumes it's launched as a local stdio subprocess,
which is the simplest option during development.
"""
import json
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioServerParameters

from app.config import settings

_RULES_PATH = Path(__file__).parent / "policy_rules.json"
_POLICY_RULES = json.loads(_RULES_PATH.read_text())

# v1: only expose Local Posts tools. Widen this list in Phase 7
# (reviews -> Q&A -> insights) — the MCP server itself doesn't change,
# only which of its tools the agent is allowed to see.
V1_ALLOWED_TOOLS = [
    "get_local_posts",
    "create_local_post",
    "update_local_post",
    "delete_local_post",
]


def _policy_slice_for(post_type: str) -> dict:
    """Only serve the rules relevant to the post type being drafted —
    not the whole ruleset on every call."""
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

Business content profile (tone, services, pillars, keywords):
{json.dumps(content_profile, indent=2)}
{few_shot_block}
You are drafting a "{post_type}" post. Follow these policy rules exactly —
they will be enforced by a separate validator, so treat them as hard
constraints, not suggestions:
{json.dumps(policy_slice, indent=2)}

Output ONLY the post content as JSON with fields matching the post type's
required_fields above. Do not include phone numbers, emails, or URLs in the
body — use the CTA field for calls to action. Do not call any tool other
than the Local Posts tools available to you, and only call
create_local_post/update_local_post after being explicitly told the draft
was approved.
"""


def build_mcp_toolset() -> McpToolset:
    """
    Points ADK's McpToolset at the forked MCP server subprocess, filtered
    to the v1 tool allowlist.

    jmdurant/gbp-mcp-server is Node/TypeScript, not Python — it's built with
    `npm run build` and run as `node build/index.js` over stdio. Adjust the
    `cwd` below to wherever mcp_server/ ends up relative to this backend
    once deployed (see mcp_server/README.md).
    """
    return McpToolset(
        connection_params=StdioServerParameters(
            command="node",
            args=["build/index.js"],
            cwd="./mcp_server",  # path to the forked server relative to the process running this
        ),
        tool_filter=V1_ALLOWED_TOOLS,
    )


def build_agent(post_type: str, content_profile: dict, few_shot_posts: list[dict]) -> LlmAgent:
    return LlmAgent(
        model=settings.GEMINI_MODEL,
        name="gbp_post_writer",
        instruction=build_system_prompt(post_type, content_profile, few_shot_posts),
        tools=[build_mcp_toolset()],
    )
