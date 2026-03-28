"""
StreetSense -- Auth API Endpoints

Endpoints:
  POST /auth/signup     Create new account
  POST /auth/login      Login and get JWT token
  GET  /auth/me         Get current user profile
  PUT  /auth/me         Update profile
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserSignup, UserLogin, TokenResponse, UserResponse, UserUpdate
from app.services.auth_service import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: UserSignup, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account and return a JWT token.
    """
    try:
        user = await create_user(
            db=db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            phone=body.phone,
            city=body.city,
            state=body.state,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()

    role = user.role.value if hasattr(user.role, "value") else user.role
    token = create_access_token(str(user.id), user.email, role)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password. Returns a JWT token.
    """
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = user.role.value if hasattr(user.role, "value") else user.role
    token = create_access_token(str(user.id), user.email, role)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    if body.city is not None:
        current_user.city = body.city
    if body.state is not None:
        current_user.state = body.state

    await db.flush()
    await db.refresh(current_user)
    await db.commit()

    return UserResponse.model_validate(current_user)
