from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

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


@auth_router.post("/logout/{jti}")
async def user_logout(jti: str):
    if not jti or not jti.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid token identifier (jti)",
        )
    await add_jti_to_blacklist(jti.strip())
    return {"message": "Logout successful"}
