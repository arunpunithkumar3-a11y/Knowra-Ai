from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependency import verify_token
from models.buisness_schemas import BusinessCreate, BusinessUpdate
from services.buisness import BuisnessService
from src.core.main import get_session

buisness_service = BuisnessService()
buisness_router = APIRouter()


@buisness_router.get("/buisness{buisness_id}")
async def get_buisness(
    buisness_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):

    buisness = await buisness_service.get_businesses_by_owner(
        buisness_id=buisness_id, session=session
    )
    return JSONResponse(content=buisness, status_code=status.HTTP_200_OK)


@buisness_router.get("/all_buisness{user_id}")
async def get_all_buisness(
    user_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):

    user_id = token_details["user_data"]["user_id"]
    all_buisness = await buisness_service.get_businesses_by_owner(
        owner_id=user_id, session=session
    )
    return JSONResponse(content=all_buisness, status_code=status.HTTP_200_OK)


@buisness_router.post("/create_buisness")
async def create_buisness(
    data: BusinessCreate,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    user_id = token_details["user_data"]["user_id"]
    new_buisness = await buisness_service.create_business(
        business_data=data, owner_id=user_id, session=session
    )
    return JSONResponse(
        content={"message": new_buisness},
        status_code=status.HTTP_201_CREATED,
    )


@buisness_router.put("/update_buisness{buisness_id}")
async def update_buisness(
    buisness_id: str,
    data: BusinessUpdate,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    buisness = await buisness_service.update_business(
        buisness_id=buisness_id, buisness_data=data, session=session
    )
    if not buisness:
        raise HTTPException(
            detail="Buisness does not exist", status_code=status.HTTP_404_NOT_FOUND
        )

    return buisness


@buisness_router("/delete_buisness{buisness_id}")
async def deleted_buisness(
    buisness_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    buisness = await buisness_service.delete_business(
        buisness_id=buisness_id, session=session
    )
    if not buisness:
        raise HTTPException(
            detail="Buisness does not exist", status_code=status.HTTP_404_NOT_FOUND
        )

    return buisness
