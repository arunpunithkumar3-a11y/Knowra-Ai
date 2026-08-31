from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependency import verify_any_token, verify_refresh_token
from src.core.main import get_session
from src.core.password import verify_password
from src.core.redis import add_jti_to_blacklist
from src.core.security import create_access_token
from src.models.auth_schemas import UserLogin, UserSignup
from src.services.user import UserService

auth_router = APIRouter()

REFRESH_TOKEN_EXPIRY_DAYS = 2

user_service = UserService()


def get_user_service() -> UserService:
    return user_service


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def user_signup(
    data: UserSignup,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    if await service.user_exists(data.email, session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    await service.create_user(data, session)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Account created successfully"},
    )


@auth_router.post("/login")
async def user_login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    user = await service.get_user_by_email(data.email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(
        data={"email": user.email, "user_id": str(user.uid)}
    )
    refresh_token = create_access_token(
        data={"email": user.email, "user_id": str(user.uid)},
        refresh=True,
        expire=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token, "refresh_token": refresh_token},
    )


@auth_router.post("/refresh")
async def refresh_token_endpoint(
    token_details: dict = Depends(verify_refresh_token),
):
    user_data = token_details.get("user_data", {})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    old_jti = token_details.get("jti")
    if old_jti:
        await add_jti_to_blacklist(old_jti)

    new_access_token = create_access_token(data=user_data)
    new_refresh_token = create_access_token(
        data=user_data,
        refresh=True,
        expire=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        },
    )


@auth_router.post("/logout")
async def user_logout(
    token_details: dict = Depends(verify_any_token),
):
    jti = token_details.get("jti")
    if jti:
        await add_jti_to_blacklist(jti)
    return {"message": "Logout successful"}


@auth_router.post("/logout/{jti}")
async def user_logout_by_param(jti: str):
    if not jti or not jti.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid token identifier (jti)",
        )
    await add_jti_to_blacklist(jti.strip())
    return {"message": "Logout successful"}
