import os
import sys
import json
import asyncio
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.getcwd())

from app.main import app
from app.agent.validator import validate_post
from app.email.templates import draft_preview_email, connection_confirmed_email
from app.credentials.store import _encrypt, _decrypt
from app.config import settings

client = TestClient(app)

def print_result(name, success, message=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name}: {message}")

async def run_smoke_tests():
    print("Starting Trendit Smoke Test...\n")

    # 1. Backend Health (Local)
    try:
        response = client.get("/health")
        success = response.status_code == 200 and response.json() == {"status": "ok"}
        print_result("Local /health", success, f"Status: {response.status_code}")
    except Exception as e:
        print_result("Local /health", False, str(e))

    # 2. Debug DB (Local)
    try:
        response = client.get("/debug/db")
        data = response.json()
        # pool_initialized: true is what we want to see if the pool setup worked
        success = data.get("pool_initialized") == True
        print_result("Local /debug/db", success, f"Data: {data}")
    except Exception as e:
        print_result("Local /debug/db", False, str(e))

    # 3. Validator Check
    try:
        # Standard post
        standard_content = {
            "title": "Welcome to Trendit",
            "body": "This is a test post.",
            "cta": "LEARN_MORE"
        }
        res = validate_post("standard", standard_content)
        print_result("Validator (Standard)", res.passed, f"Errors: {res.errors}")

        # Invalid post (URL in body)
        invalid_content = {
            "title": "Bad Post",
            "body": "Visit us at https://trendit.com",
            "cta": "LEARN_MORE"
        }
        res_invalid = validate_post("standard", invalid_content)
        print_result("Validator (Rejection)", not res_invalid.passed, f"Should fail: {not res_invalid.passed}. Errors: {res_invalid.errors}")
    except Exception as e:
        print_result("Validator", False, str(e))

    # 4. Email Template Rendering
    try:
        subject, body = draft_preview_email("123", "standard", {"title": "Test", "body": "Body", "cta": "CTA"}, "http://test")
        success = "Test" in body and "http://test/approve/123" in body
        print_result("Email Template (Draft)", success)

        subject, body = connection_confirmed_email("My Business", "loc_123")
        success = "My Business" in body and "loc_123" in body
        print_result("Email Template (Connect)", success)
    except Exception as e:
        print_result("Email Templates", False, str(e))

    # 5. Encryption / Credentials check
    try:
        # Test encryption round-trip
        token = "test-token-123"
        encrypted = _encrypt(token)
        decrypted = _decrypt(encrypted)
        success = token == decrypted
        print_result("Encryption Round-trip", success)
    except Exception as e:
        print_result("Encryption", False, str(e))

    # 6. Live Health Check (Optional)
    import httpx
    async with httpx.AsyncClient() as hclient:
        try:
            resp = await hclient.get("https://trendit-4ocu.onrender.com/health", timeout=5.0)
            print_result("Live /health", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            # We don't fail the whole test if the live site is down or unreachable
            print_result("Live /health", False, "Skipping or unreachable: " + str(e))

    print("\nSmoke Test Complete.")

if __name__ == "__main__":
    asyncio.run(run_smoke_tests())
