from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.main import get_session
from src.core.security import get_current_user
from src.models.database import User
from src.models.org_schemas import OrgCreate, OrgRead, OrgUpdate
from src.services.org import OrgService

org_router = APIRouter(prefix="/orgs", tags=["Organizations"])


async def get_org_service(session: AsyncSession = Depends(get_session)) -> OrgService:
    return OrgService(session)


@org_router.post("", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    org_data: OrgCreate,
    current_user: User = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
):
    org = await org_service.create_org(org_data, current_user.uid)
    return org


@org_router.get("", response_model=list[OrgRead])
async def list_orgs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    org_service: OrgService = Depends(get_org_service),
):
    return await org_service.get_all_orgs(skip=skip, limit=limit)


@org_router.get("/my-orgs", response_model=list[OrgRead])
async def list_my_orgs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
):
    return await org_service.get_orgs_by_user(current_user.uid, skip=skip, limit=limit)


@org_router.get("/{org_id}", response_model=OrgRead)
async def get_org(
    org_id: UUID,
    org_service: OrgService = Depends(get_org_service),
):
    org = await org_service.get_org_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organization not found"},
        )
    return org


@org_router.get("/{org_id}/members")
async def get_org_members(
    org_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    org_service: OrgService = Depends(get_org_service),
):
    org = await org_service.get_org_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organization not found"},
        )
    return await org_service.get_org_members(org_id, skip=skip, limit=limit)


@org_router.put("/{org_id}", response_model=OrgRead)
async def update_org(
    org_id: UUID,
    org_data: OrgUpdate,
    current_user: User = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
):
    org = await org_service.get_org_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organization not found"},
        )
    if org.user_id != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not authorized to update this organization"},
        )
    return await org_service.update_org(org_data, org)


@org_router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
):
    org = await org_service.get_org_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organization not found"},
        )
    if org.user_id != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not authorized to delete this organization"},
        )
    await org_service.delete_org(org_id)
    return None
