from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import require_roles
from app.modules.companies.schemas import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from app.modules.companies.service import (
    create_company,
    get_companies,
    get_company_by_id,
    update_company,
)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Company"
)
async def create_new_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await create_company(db, data, current_user)


@router.get(
    "",
    response_model=list[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="List Companies"
)
async def list_companies(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db)
):
    return await get_companies(db, limit=limit, offset=offset)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Company by ID"
)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_company_by_id(db, company_id)


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Company"
)
async def update_existing_company(
    company_id: UUID,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await update_company(db, company_id, data, current_user)

