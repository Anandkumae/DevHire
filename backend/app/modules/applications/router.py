from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user, require_roles
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.modules.applications.service import (
    apply_to_job,
    get_application_by_id,
    get_candidate_applications,
    get_job_applications,
    update_application_status,
)

router = APIRouter(
    prefix="/applications",
    tags=["Applications"]
)


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a Job"
)
async def submit_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await apply_to_job(db, data, current_user)


@router.get(
    "/me",
    response_model=list[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current Candidate's Applications"
)
async def list_my_applications(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await get_candidate_applications(db, current_user.id, limit=limit, offset=offset)


@router.get(
    "/job/{job_id}",
    response_model=list[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Applicants for a Job (Recruiter/Admin)"
)
async def list_job_applicants(
    job_id: UUID,
    status: str | None = Query(None, description="Filter by application status"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await get_job_applications(
        db=db,
        job_id=job_id,
        current_user=current_user,
        status_filter=status,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Details & Audit Timeline"
)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_application_by_id(db, application_id, current_user)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application Status (Recruiter/Admin)"
)
async def change_application_status(
    application_id: UUID,
    data: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await update_application_status(db, application_id, data, current_user)
