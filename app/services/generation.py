"""
Post generation orchestrator. Coordinates the LLM agent, deterministic
validator, and notification services to produce and deliver post drafts.
"""
import json
from contextlib import AsyncExitStack
from google.adk.tools.mcp_tool import MCPToolset

from app.agent.agent import build_agent, get_mcp_server_params, V1_ALLOWED_TOOLS
from app.agent.content_profile import get_content_profile, get_recent_approved_posts
from app.agent.validator import validate_post
from app.services.post_history import create_draft, save_validator_result
from app.services.notify import send_draft_for_approval

async def generate_post_draft(customer_id: str, location_id: str, post_type: str = "standard") -> str:
    """
    The main generation loop:
      1. Assemble context (profile + few-shot examples)
      2. Call LLM agent for a draft
      3. Run deterministic validator
      4. Save to post_history
      5. Trigger notifications (Email + Telegram)
    """
    # 1. Context
    profile = await get_content_profile(customer_id, location_id)
    if not profile:
        raise ValueError(f"No content profile found for customer {customer_id}")
    
    few_shots = await get_recent_approved_posts(customer_id, location_id)
    
    # 2. Load MCP Tools for the agent
    async with AsyncExitStack() as stack:
        toolset = MCPToolset(
            connection_params=get_mcp_server_params(),
            exit_stack=stack
        )
        await stack.enter_async_context(toolset)
        all_tools = await toolset.load_tools()
        filtered_tools = [t for t in all_tools if t.name in V1_ALLOWED_TOOLS]
        
        # 3. Agent call
        agent = build_agent(post_type, profile, few_shots, tools=filtered_tools)
        # Using a simple prompt as the system instruction handles the heavy lifting
        response = await agent.run(f"Draft a new {post_type} post for this business.")
        
        # Extract JSON content from agent response
        # ADK response structure can vary; assuming it returns a text string or a message object
        content_text = response.text if hasattr(response, "text") else str(response)
        try:
            # LLM might wrap in markdown blocks
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()
            
            draft_content = json.loads(content_text)
        except Exception as e:
            raise RuntimeError(f"Failed to parse agent response as JSON: {content_text}") from e

    # 4. Validation (outside the async context stack is fine as we have the content)
    val_result = validate_post(post_type, draft_content)
    
    # 5. Persistence
    post_id = await create_draft(
        customer_id=customer_id,
        location_id=location_id,
        post_type=post_type,
        draft_content=draft_content
    )
    
    # Save validator results and auto-fixed content if any
    await save_validator_result(
        post_id=post_id,
        validator_result={
            "passed": val_result.passed,
            "errors": val_result.errors,
            "auto_fixed_fields": val_result.auto_fixed_fields
        },
        fixed_content=val_result.fixed_content
    )
    
    # 6. Notification
    # The requirement said to trigger both Telegram and Email.
    # notify.send_draft_for_approval will handle both.
    await send_draft_for_approval(post_id)
    
    return post_id

