from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    Company,
    Interview,
    Job,
    User,
)
from app.modules.admin.schemas import AdminPlatformStats, AdminUserStatusUpdate


async def list_users_for_admin(
    db: AsyncSession,
    role: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0
) -> list[User]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def update_user_moderation_status(
    db: AsyncSession,
    user_id: UUID,
    data: AdminUserStatusUpdate
) -> User:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role is not None:
        user.role = data.role

    await db.commit()
    await db.refresh(user)
    return user


async def get_system_platform_stats(db: AsyncSession) -> AdminPlatformStats:
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_candidates = (await db.execute(select(func.count(User.id)).where(User.role == "candidate"))).scalar() or 0
    total_recruiters = (await db.execute(select(func.count(User.id)).where(User.role == "recruiter"))).scalar() or 0
    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    published_jobs = (await db.execute(select(func.count(Job.id)).where(Job.status == "published"))).scalar() or 0
    total_applications = (await db.execute(select(func.count(Application.id)))).scalar() or 0
    total_interviews = (await db.execute(select(func.count(Interview.id)))).scalar() or 0

    return AdminPlatformStats(
        total_users=total_users,
        total_candidates=total_candidates,
        total_recruiters=total_recruiters,
        total_companies=total_companies,
        total_jobs=total_jobs,
        published_jobs=published_jobs,
        total_applications=total_applications,
        total_interviews=total_interviews
    )

