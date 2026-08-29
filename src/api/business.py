from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependency import verify_token
from src.core.main import get_session
from src.models.business_schemas import BusinessCreate, BusinessUpdate
from src.services.business import BusinessService

business_service = BusinessService()
business_router = APIRouter()


def _parse_uuid(value: str, field_name: str = "ID") -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format",
        )


@business_router.get("/business/{business_id}")
async def get_business(
    business_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(business_id, "business ID")
    business = await business_service.get_business_by_id(
        business_id=b_uuid, session=session
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    return business


@business_router.get("/all_business")
async def get_all_business(
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
    all_business = await business_service.get_businesses_by_owner(
        owner_id=u_uuid, session=session
    )
    return all_business


@business_router.post("/create_business", status_code=status.HTTP_201_CREATED)
async def create_business(
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
    new_business = await business_service.create_business(
        business_data=data, owner_id=u_uuid, session=session
    )
    return new_business


@business_router.put("/update_business/{business_id}")
async def update_business(
    business_id: str,
    data: BusinessUpdate,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(business_id, "business ID")
    business = await business_service.update_business(
        business_id=b_uuid, business_data=data, session=session
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business does not exist",
        )
    return business


@business_router.delete("/delete_business/{business_id}")
async def deleted_business(
    business_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    b_uuid = _parse_uuid(business_id, "business ID")
    business = await business_service.delete_business(
        business_id=b_uuid, session=session
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business does not exist",
        )
    return {"message": "Business deleted successfully", "business_id": str(b_uuid)}
