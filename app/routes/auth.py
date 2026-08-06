from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from app.db import get_pool
from app.auth_utils import get_password_hash, verify_password, create_access_token
import uuid
import logging

router = APIRouter()

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(user: UserRegister):
    pool = get_pool()
    
    # Check if username is taken by someone else
    existing_username = await pool.fetchrow(
        "SELECT email FROM customers WHERE username = $1 AND email != $2",
        user.username, user.email
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if email already has a password (only if they aren't trying to overwrite their own)
    existing_pwd = await pool.fetchval(
        "SELECT password_hash FROM customers WHERE email = $1",
        user.email
    )
    if existing_pwd:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already has a password. Please log in."
        )
    
    hashed_pwd = get_password_hash(user.password)
    
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO customers (email, username, password_hash)
            VALUES ($1, $2, $3)
            ON CONFLICT (email) DO UPDATE SET
                username = COALESCE(EXCLUDED.username, customers.username),
                password_hash = COALESCE(EXCLUDED.password_hash, customers.password_hash),
                updated_at = now()
            RETURNING customer_id
            """,
            user.email, user.username, hashed_pwd
        )
        
        customer_id = str(row["customer_id"])
        access_token = create_access_token(data={"sub": customer_id, "email": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "customer_id": customer_id,
            "email": user.email,
            "username": user.username
        }
    except Exception as e:
        logging.exception(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")

@router.post("/login")
async def login(credentials: UserLogin):
    pool = get_pool()
    
    row = await pool.fetchrow(
        "SELECT customer_id, email, username, password_hash FROM customers WHERE email = $1",
        credentials.email
    )
    
    if not row or not row["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    customer_id = str(row["customer_id"])
    access_token = create_access_token(data={"sub": customer_id, "email": row["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "customer_id": customer_id,
        "email": row["email"],
        "username": row["username"]
    }

