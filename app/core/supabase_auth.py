"""
Supabase Authentication Integration for FastAPI
"""

import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Client
from app.core.config import settings

# Supabase configuration from settings
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

# Token security
security = HTTPBearer()

class SupabaseUser:
    """Represents a Supabase user from JWT token"""
    def __init__(self, user_id: str, email: str, **kwargs):
        self.id = user_id
        self.email = email
        self.metadata = kwargs

def verify_supabase_token(token: str) -> Optional[SupabaseUser]:
    """Verify and decode a Supabase JWT token"""
    try:
        # First, let's try without audience verification for debugging
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Disable audience verification for now
        )

        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")

        # Debug logging
        print(f"🔍 JWT Payload: {payload}")
        print(f"👤 User ID: {user_id}")
        print(f"📧 Email: {email}")

        if not user_id:
            print("❌ No user ID found in token")
            return None

        # Create a clean payload without conflicting keys
        clean_payload = {k: v for k, v in payload.items() if k not in ['email']}

        return SupabaseUser(
            user_id=user_id,
            email=email or "unknown@example.com",
            **clean_payload
        )

    except jwt.ExpiredSignatureError as e:
        print(f"❌ Token expired: {e}")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {e}")
        return None
    except Exception as e:
        print(f"❌ Token verification error: {e}")
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SupabaseUser:
    """Get the current authenticated user from Supabase token"""
    print(f"🔑 Received token: {credentials.credentials[:50]}...")
    print(f"🔐 JWT Secret configured: {'Yes' if SUPABASE_JWT_SECRET else 'No'}")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not SUPABASE_JWT_SECRET:
        print("❌ SUPABASE_JWT_SECRET not configured!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: JWT secret not set"
        )

    token = credentials.credentials
    user = verify_supabase_token(token)

    if user is None:
        print("❌ Token verification failed")
        raise credentials_exception

    print(f"✅ User authenticated: {user.email}")
    return user

def get_current_active_user(current_user: SupabaseUser = Depends(get_current_user)) -> SupabaseUser:
    """Get the current active user (Supabase users are always active)"""
    return current_user

def verify_client_ownership(
    client_id: int,
    current_user: SupabaseUser,
    db: Session
) -> Client:
    """Verify that a client belongs to the current user"""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or access denied"
        )
    
    return client

# Optional: For development/testing without Supabase JWT secret
def get_mock_user() -> SupabaseUser:
    """Mock user for development (remove in production)"""
    return SupabaseUser(
        user_id="mock-user-id",
        email="dev@example.com"
    )

# Use this for development if you don't have Supabase JWT secret yet
def get_current_user_dev(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SupabaseUser:
    """Development version that accepts any token"""
    # In development, you can use this to bypass real Supabase verification
    # Remove this in production!
    return get_mock_user()
