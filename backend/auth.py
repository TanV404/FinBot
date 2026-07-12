import os
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client, acreate_client, Client, AsyncClient
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be configured in environment")

# Standard sync client initialized for retriever operations that must remain synchronous.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY)

# Lazy Async client initialization for high-concurrency FastAPI routes.
_async_supabase: AsyncClient = None

async def get_async_supabase() -> AsyncClient:
    global _async_supabase
    if _async_supabase is None:
        _async_supabase = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY)
    return _async_supabase

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    FastAPI dependency to verify Supabase JWT token asynchronously.
    Calls Supabase auth.get_user to confirm token validity.
    Returns a dictionary with the verified user's details.
    """
    token = credentials.credentials
    try:
        client = await get_async_supabase()
        res = await client.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid Supabase JWT token")
        return {
            "id": res.user.id,
            "email": res.user.email,
            "role": res.user.role,
            "token": token
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {str(e)}"
        )

async def verify_admin(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    FastAPI dependency to verify Supabase JWT token AND check for admin role claim in app_metadata.
    """
    token = credentials.credentials
    # First verify token is valid via Supabase Auth asynchronously
    user_info = await verify_token(credentials)
    
    try:
        # Decode the payload to read claims
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Supabase stores user role claims in app_metadata
        app_metadata = payload.get("app_metadata", {})
        role = app_metadata.get("role") or payload.get("role")
        
        if role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Stricter verification failed: admin role claim required"
            )
            
        user_info["admin_role"] = role
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to parse JWT claims: {str(e)}"
        )
