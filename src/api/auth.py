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


@auth_router.post("/signup")
async def user_signup(
    data: UserSignup,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
):
    if await user_service.user_exists(data.email, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "user with this email already exists"},
        )
    user = await user_service.create_user(data, session)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Account created successfully"},
    )


@auth_router.post("/login")
async def user_login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.get_user_by_email(data.email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Account does not exist"},
        )
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Invalid credentials"},
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
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Please provide a access token"},
        )
    add_jti_to_blacklist(jti)
    return {"message": "Logout successfull"}
