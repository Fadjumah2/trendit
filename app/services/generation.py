"""
Post generation orchestrator. Coordinates the LLM agent, deterministic
validator, and notification services to produce and deliver post drafts.
"""
import json
import uuid
from contextlib import AsyncExitStack
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.session import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.run_config import RunConfig
from app.agent.agent import build_agent, get_mcp_server_params, V1_ALLOWED_TOOLS
from app.agent.content_profile import get_content_profile, get_recent_approved_posts
from app.agent.validator import validate_post
from app.services.post_history import create_draft, save_validator_result
from app.services.notify import send_draft_for_approval

async def generate_post_draft(customer_id: str, location_id: str, post_type: str = "standard") -> str:
    profile = await get_content_profile(customer_id, location_id)
    if not profile:
        raise ValueError(f"No content profile found for customer {customer_id}")
    few_shots = await get_recent_approved_posts(customer_id, location_id)
    
    # Use the from_server factory method as documented in ADK
    all_tools, toolset_stack = await MCPToolset.from_server(
        connection_params=get_mcp_server_params()
    )
    
    try:
        filtered_tools = [t for t in all_tools if t.name in V1_ALLOWED_TOOLS]
        agent = build_agent(post_type, profile, few_shots, tools=filtered_tools)
        session_service = InMemorySessionService()
        session = session_service.create_session(app_name="post_writer", user_id=customer_id)
        ctx = InvocationContext(
            invocation_id="e-" + str(uuid.uuid4()),
            session=session,
            session_service=session_service,
            run_config=RunConfig(response_modalities=["TEXT"]),
            agent=agent
        )
        content_text = ""
        async for event in agent.run_async(ctx):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        content_text += part.text
        try:
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()
            draft_content = json.loads(content_text)
        except Exception as e:
            raise RuntimeError(f"Failed to parse agent response as JSON: {content_text}") from e
    finally:
        await toolset_stack.aclose()
    
    val_result = validate_post(post_type, draft_content)
    post_id = await create_draft(customer_id=customer_id, location_id=location_id, post_type=post_type, draft_content=draft_content)
    await save_validator_result(post_id=post_id, validator_result={"passed": val_result.passed, "errors": val_result.errors, "auto_fixed_fields": val_result.auto_fixed_fields}, fixed_content=val_result.fixed_content)
    await send_draft_for_approval(post_id)
    return post_id
