"""
StreetSense -- Auth Service

Handles:
  - Password hashing (bcrypt)
  - JWT token creation/verification
  - User signup/login
  - FastAPI dependency for protected routes
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token extractor
security = HTTPBearer(auto_error=False)


# ===================================================================
# Password Utilities
# ===================================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ===================================================================
# JWT Token Utilities
# ===================================================================

def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# ===================================================================
# User CRUD
# ===================================================================

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    phone: str = None,
    city: str = None,
    state: str = None,
    role: str = "citizen",
) -> User:
    """Create a new user account."""
    # Check if email already exists
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("An account with this email already exists")

    user = User(
        id=uuid.uuid4(),
        email=email.lower().strip(),
        full_name=full_name.strip(),
        phone=phone,
        hashed_password=hash_password(password),
        role=role,
        city=city,
        state=state,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"User created: {email} (role={role})")
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Verify email and password, return user or None."""
    user = await get_user_by_email(db, email.lower().strip())
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ===================================================================
# FastAPI Dependencies (protect routes)
# ===================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: extract and verify JWT from Authorization header.
    Use in route: current_user: User = Depends(get_current_user)
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_id(db, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Same as get_current_user but returns None instead of raising 401."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await get_user_by_id(db, uuid.UUID(user_id))
    return user if user and user.is_active else None


def require_role(*roles: str):
    """Dependency factory: require user to have one of the specified roles."""
    async def checker(current_user: User = Depends(get_current_user)):
        user_role = current_user.role
        if hasattr(user_role, "value"):
            user_role = user_role.value
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(roles)}",
            )
        return current_user
    return checker
