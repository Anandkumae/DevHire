from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import require_roles
from app.modules.admin.schemas import (
    AdminPlatformStats,
    AdminUserListItem,
    AdminUserStatusUpdate,
)
from app.modules.admin.service import (
    get_system_platform_stats,
    list_users_for_admin,
    update_user_moderation_status,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Moderation"]
)


@router.get(
    "/users",
    response_model=list[AdminUserListItem],
    status_code=status.HTTP_200_OK,
    summary="List Users for Moderation"
)
async def list_users(
    role: str | None = Query(None, description="Filter by user role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin"))
):
    return await list_users_for_admin(db, role=role, is_active=is_active, limit=limit, offset=offset)


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUserListItem,
    status_code=status.HTTP_200_OK,
    summary="Moderate User Account Status"
)
async def update_user_status(
    user_id: UUID,
    data: AdminUserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin"))
):
    return await update_user_moderation_status(db, user_id, data)


@router.get(
    "/stats",
    response_model=AdminPlatformStats,
    status_code=status.HTTP_200_OK,
    summary="System-wide Platform Statistics"
)
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin"))
):
    return await get_system_platform_stats(db)

