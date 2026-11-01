from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, User
from app.modules.companies.schemas import CompanyCreate, CompanyUpdate


async def create_company(
    db: AsyncSession,
    data: CompanyCreate,
    current_user: User
) -> Company:
    existing = await db.execute(
        select(Company).where(Company.recruiter_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a registered company"
        )

    company = Company(
        name=data.name,
        description=data.description,
        website=str(data.website) if data.website else None,
        industry=data.industry,
        location=data.location,
        recruiter_id=current_user.id
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


async def get_companies(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0
) -> list[Company]:
    stmt = (
        select(Company)
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_company_by_id(
    db: AsyncSession,
    company_id: UUID
) -> Company:
    stmt = select(Company).where(Company.id == company_id)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return company


async def update_company(
    db: AsyncSession,
    company_id: UUID,
    data: CompanyUpdate,
    current_user: User
) -> Company:
    company = await get_company_by_id(db, company_id)

    # Recruiters can only modify their own company; Admins can modify any
    if current_user.role != "admin" and company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this company"
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "website" and value is not None:
            value = str(value)
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    return company

