from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependency import verify_token
from src.core.main import get_session
from src.models.buisness_schemas import BusinessCreate, BusinessUpdate
from src.services.buisness import BuisnessService

buisness_service = BuisnessService()
buisness_router = APIRouter()


def _parse_uuid(value: str, field_name: str = "ID") -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format",
        )


@buisness_router.get("/buisness/{buisness_id}")
async def get_buisness(
    buisness_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(buisness_id, "business ID")
    buisness = await buisness_service.get_business_by_id(
        business_id=b_uuid, session=session
    )
    if not buisness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    return buisness


@buisness_router.get("/all_buisness")
async def get_all_buisness(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    all_buisness = await buisness_service.get_businesses_by_owner(
        owner_id=u_uuid, session=session
    )
    return all_buisness


@buisness_router.post("/create_buisness", status_code=status.HTTP_201_CREATED)
async def create_buisness(
    data: BusinessCreate,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    if not data.business_name or not data.business_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business name is required",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    new_buisness = await buisness_service.create_business(
        business_data=data, owner_id=u_uuid, session=session
    )
    return new_buisness


@buisness_router.put("/update_buisness/{buisness_id}")
async def update_buisness(
    buisness_id: str,
    data: BusinessUpdate,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(buisness_id, "business ID")
    buisness = await buisness_service.update_business(
        business_id=b_uuid, business_data=data, session=session
    )
    if not buisness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business does not exist",
        )
    return buisness


@buisness_router.delete("/delete_buisness/{buisness_id}")
async def deleted_buisness(
    buisness_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(buisness_id, "business ID")
    buisness = await buisness_service.delete_business(
        business_id=b_uuid, session=session
    )
    if not buisness:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business does not exist",
        )
    return {"message": "Business deleted successfully", "buisness_id": str(b_uuid)}
