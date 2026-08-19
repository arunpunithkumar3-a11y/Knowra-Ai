from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependency import verify_token
from models.buisness_schemas import BusinessCreate
from services.buisness import BuisnessService
from src.core.main import get_session

buisness_service = BuisnessService()
buisness_router = APIRouter()


@buisness_router.post("/create_buiness")
async def create(
    data: BusinessCreate,
    session: AsyncSession = Depends(get_session),
    token_details=Depends(verify_token),
):
    pass
