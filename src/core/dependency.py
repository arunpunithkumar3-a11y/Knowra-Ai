from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.redis import token_in_blaclist
from src.core.security import decode_access_token

security = HTTPBearer()


async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"messages": "Invalid or expired token"},
        )
    jti = token_data.get("jti")
    if jti and await token_in_blaclist(jti):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"messages": "Token revoked get a new access token"},
        )
    return token_data
