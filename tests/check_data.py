import asyncio
import os
import asyncpg
import json
from app.db import init_pool, get_pool, close_pool
from app.credentials.store import _decrypt

async def check_db():
    print("Connecting to DB...")
    # Production key from Render env vars
    os.environ["CREDENTIALS_ENCRYPTION_KEY"] = "kX7bH2pQmN9vR4tY6wE1sJ8dF0zA3cL5gU2hI9oP7kX="
    
    # Use external URL for local execution
    external_url = "postgresql://trendit_db_vpvw_user:tYajjpC74z1qwDbEFossugXfE98Zjy0m@dpg-d9j55i7aqgkc73b074bg-a.virginia-postgres.render.com/trendit_db_vpvw"
    _pool = await asyncpg.create_pool(dsn=external_url, ssl="require")
    
    customers = await _pool.fetch("SELECT customer_id, email, business_name, created_at FROM customers ORDER BY created_at DESC LIMIT 5")
    print("\n--- RECENT CUSTOMERS ---")
    for c in customers:
        print(f"ID: {c['customer_id']} | Email: {c['email']} | Biz: {c['business_name']}")
        
    creds = await _pool.fetch("SELECT customer_id, location_id, account_id, access_token FROM gbp_credentials ORDER BY created_at DESC LIMIT 5")
    print("\n--- RECENT CREDENTIALS ---")
    for r in creds:
        try:
            token = _decrypt(r['access_token'])
            print(f"Cust: {r['customer_id']} | Loc: {r['location_id']} | Token: {token[:15]}...")
        except Exception as e:
            print(f"Cust: {r['customer_id']} | Error decrypting: {str(e)}")
        
    await _pool.close()
        
    await _pool.close()

if __name__ == "__main__":
    asyncio.run(check_db())
