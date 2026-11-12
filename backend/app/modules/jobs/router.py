from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache, invalidate_cache_pattern, set_cache
from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import require_roles
from app.modules.jobs.schemas import JobCreate, JobResponse, JobUpdate
from app.modules.jobs.service import (
    close_job,
    create_job,
    delete_job,
    get_job,
    list_jobs,
    update_job,
)

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job"
)
async def create_new_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    job = await create_job(db, data, current_user)
    await invalidate_cache_pattern("jobs:list:*")
    return job


@router.get(
    "",
    response_model=list[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="Browse & Search Jobs"
)
async def browse_jobs(
    search: str | None = Query(None, description="Search in job title or description"),
    location: str | None = Query(None, description="Filter by location"),
    employment_type: str | None = Query(None, description="Filter by employment type"),
    experience_level: str | None = Query(None, description="Filter by experience level"),
    min_salary: Decimal | None = Query(None, ge=0, description="Minimum salary overlap"),
    max_salary: Decimal | None = Query(None, ge=0, description="Maximum salary overlap"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"jobs:list:{search}:{location}:{employment_type}:{experience_level}:{min_salary}:{max_salary}:{limit}:{offset}"
    cached_data = await get_cache(cache_key)
    if cached_data is not None:
        return JSONResponse(content=cached_data, headers={"X-Cache": "HIT"})

    jobs = await list_jobs(
        db=db,
        search=search,
        location=location,
        employment_type=employment_type,
        experience_level=experience_level,
        min_salary=min_salary,
        max_salary=max_salary,
        limit=limit,
        offset=offset
    )
    serialized = [JobResponse.model_validate(j).model_dump(mode="json") for j in jobs]
    await set_cache(cache_key, serialized, ttl_seconds=60)
    return JSONResponse(content=serialized, headers={"X-Cache": "MISS"})


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Details"
)
async def get_job_details(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_job(db, job_id)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Job"
)
async def update_existing_job(
    job_id: UUID,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    job = await update_job(db, job_id, data, current_user)
    await invalidate_cache_pattern("jobs:list:*")
    return job


@router.patch(
    "/{job_id}/close",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Close Job"
)
async def close_existing_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    job = await close_job(db, job_id, current_user)
    await invalidate_cache_pattern("jobs:list:*")
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Job"
)
async def delete_existing_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    result = await delete_job(db, job_id, current_user)
    await invalidate_cache_pattern("jobs:list:*")
    return result
