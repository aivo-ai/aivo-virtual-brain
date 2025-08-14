"""
Authentication and authorization utilities for the Lesson Registry service.
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from .config import get_settings

settings = get_settings()
security = HTTPBearer()


class User(BaseModel):
    """User model for authentication."""
    id: UUID
    email: str
    role: str
    name: Optional[str] = None


class TokenData(BaseModel):
    """JWT token payload structure."""
    user_id: str
    email: str
    role: str
    exp: datetime


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create JWT access token for user."""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        
        if user_id is None or email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return TokenData(
            user_id=user_id,
            email=email,
            role=role,
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token."""
    token_data = verify_token(credentials.credentials)
    
    return User(
        id=UUID(token_data.user_id),
        email=token_data.email,
        role=token_data.role
    )


def require_role(allowed_roles: List[str]):
    """Decorator factory for role-based access control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {allowed_roles}"
            )
        return current_user
    
    return role_checker


# Mock user for development/testing
def create_mock_user(role: str = "teacher") -> User:
    """Create mock user for development and testing."""
    return User(
        id=uuid4(),
        email=f"{role}@example.com",
        role=role,
        name=f"Test {role.title()}"
    )
