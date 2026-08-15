from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.core.main import get_session
from src.core.redis import add_jti_to_blacklist
from src.core.security import create_access_token
from src.models.auth import UserLogin, UserSignup
from src.services.user import UserService

user_serv = UserService()
auth_router = APIRouter()

REFRESH_TOKEN_EXPIRY_DAYS = 2


@auth_router.post("/signup")
async def user_signup(data: UserSignup, session: AsyncSession = Depends(get_session)):
    email = data.email
    if await user_serv.user_exists(email, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "user with this email already exists"},
        )
    user = await user_serv.create_user(data, session)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Account created successfully"},
    )


@auth_router.post("/login")
async def user_login(data: UserLogin, session: AsyncSession = Depends(get_session)):
    user = await user_serv.get_user_by_email(data.email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Account does not exists"},
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
