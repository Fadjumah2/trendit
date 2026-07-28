"""
Onboarding service to process raw intake and generate a business content profile.
"""
import json
from google.adk.agents import LlmAgent
from app.config import settings
from app.agent.content_profile import save_content_profile

async def complete_onboarding_process(customer_id: str, location_id: str, source_intake: dict) -> dict:
    """
    1. Distill raw intake into a structured profile using Gemini.
    2. Save the result to business_content_profiles.
    """
    agent = LlmAgent(
        model=settings.GEMINI_MODEL,
        name="onboarding_distiller",
        instruction="""You are an expert brand strategist for Google Business Profile. 
Your task is to take raw onboarding answers from a business owner and distill them into a structured profile.

The output MUST be a JSON object with these keys:
- tone: a short description of the brand voice (e.g. "Friendly and helpful")
- core_services: a list of 3-5 top services or product categories
- content_pillars: a list of 3 themes for their social posts (e.g. "Weekly Specials", "Behind the Scenes")
- target_audience: a short description of their ideal customer
- keywords: a list of 5-10 SEO keywords relevant to their business

Output ONLY the JSON object. No preamble, no markdown formatting."""
    )
    
    prompt = f"Raw onboarding intake:\n{json.dumps(source_intake, indent=2)}"
    response = await agent.run(prompt)
    
    content_text = response.text if hasattr(response, "text") else str(response)
    
    # Handle markdown blocks if the LLM includes them despite instructions
    try:
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
        
        profile_json = json.loads(content_text)
    except Exception as e:
        # Fallback to minimal profile if parsing fails
        print(f"Failed to parse onboarding response: {content_text}")
        profile_json = {
            "tone": source_intake.get("tone", "Professional"),
            "core_services": source_intake.get("services", []),
            "content_pillars": ["Updates", "Services", "Local Community"],
            "target_audience": source_intake.get("targetCustomer", "Local customers"),
            "keywords": []
        }

    await save_content_profile(
        customer_id=customer_id,
        location_id=location_id,
        profile_json=profile_json,
        source_intake_json=source_intake
    )
    
    return profile_json
