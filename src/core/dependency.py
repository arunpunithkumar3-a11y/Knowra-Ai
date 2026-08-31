from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.redis import token_in_blacklist
from src.core.security import decode_access_token

security = HTTPBearer()


async def verify_any_token(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = creds.credentials
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    jti = token_data.get("jti")
    if jti and await token_in_blacklist(jti):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token revoked, please log in again",
        )
    return token_data


async def verify_token(
    token_data: dict = Depends(verify_any_token),
) -> dict:
    if token_data.get("refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please provide a valid access token, not a refresh token",
        )
    return token_data


async def verify_refresh_token(
    token_data: dict = Depends(verify_any_token),
) -> dict:
    if not token_data.get("refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please provide a valid refresh token",
        )
    return token_data
