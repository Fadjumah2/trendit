import asyncio
import os
import asyncpg
import json

# Set the production key BEFORE importing the app logic
os.environ["CREDENTIALS_ENCRYPTION_KEY"] = "kX7bH2pQmN9vR4tY6wE1sJ8dF0zA3cL5gU2hI9oP7kX="

from app.credentials.store import _decrypt

async def check_discovery():
    print("Connecting to DB to find tokens...")
    external_url = "postgresql://trendit_db_vpvw_user:tYajjpC74z1qwDbEFossugXfE98Zjy0m@dpg-d9j55i7aqgkc73b074bg-a.virginia-postgres.render.com/trendit_db_vpvw"
    _pool = await asyncpg.create_pool(dsn=external_url, ssl="require")
    
    # Get the latest token for eritageentcare@gmail.com
    row = await _pool.fetchrow("""
        SELECT c.email, g.access_token 
        FROM customers c 
        JOIN gbp_credentials g ON c.customer_id = g.customer_id 
        WHERE c.email = 'eritageentcare@gmail.com'
        ORDER BY g.created_at DESC LIMIT 1
    """)
    
    if not row:
        print("No tokens found for eritageentcare@gmail.com")
        await _pool.close()
        return

    print(f"Decrypting token for {row['email']}...")
    try:
        token = _decrypt(row['access_token'])
        print(f"Token decrypted successfully.")
        
        # Now call Google Discovery APIs directly
        import httpx
        async with httpx.AsyncClient() as client:
            print("\n0. Verifying Token with UserInfo...")
            u_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"UserInfo Status: {u_resp.status_code}")
            print(f"UserInfo: {u_resp.json().get('email')}")

            print("\n1. Listing Accounts...")
            resp = await client.get(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Accounts Status: {resp.status_code}")
            print(f"Accounts Body: {json.dumps(resp.json(), indent=2)}")
            
            if resp.status_code == 200:
                accounts = resp.json().get("accounts", [])
                for acc in accounts:
                    acc_id = acc["name"]
                    print(f"\n2. Listing Locations for {acc_id}...")
                    loc_resp = await client.get(
                        f"https://mybusinessbusinessinformation.googleapis.com/v1/{acc_id}/locations?readMask=name,title",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    print(f"Locations Status: {loc_resp.status_code}")
                    print(f"Locations Body: {json.dumps(loc_resp.json(), indent=2)}")
    except Exception as e:
        print(f"Error during discovery: {str(e)}")
        
    await _pool.close()

if __name__ == "__main__":
    asyncio.run(check_discovery())
