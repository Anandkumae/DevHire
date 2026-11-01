from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Application, ApplicationStatusHistory, Company, Job, User
from app.modules.applications.schemas import ApplicationCreate, ApplicationStatusUpdate

VALID_STATUS_TRANSITIONS = {
    "applied": {"under_review", "rejected"},
    "under_review": {"shortlisted", "rejected"},
    "shortlisted": {"interview", "rejected"},
    "interview": {"selected", "rejected"},
    "selected": set(),
    "rejected": set(),
}


async def apply_to_job(
    db: AsyncSession,
    data: ApplicationCreate,
    current_user: User
) -> Application:
    # 1. Job must exist and be published
    job_stmt = select(Job).where(Job.id == data.job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    if job.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot apply to a {job.status} job"
        )

    # 2. Check for duplicate application
    dup_stmt = select(Application).where(
        Application.candidate_id == current_user.id,
        Application.job_id == data.job_id
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job"
        )

    # 3. Create application and initial audit log atomically
    application = Application(
        candidate_id=current_user.id,
        job_id=data.job_id,
        cover_letter=data.cover_letter,
        resume_url=data.resume_url,
        status="applied"
    )
    db.add(application)
    await db.flush()

    history = ApplicationStatusHistory(
        application_id=application.id,
        from_status=None,
        to_status="applied",
        changed_by_user_id=current_user.id,
        notes="Application submitted by candidate"
    )
    db.add(history)
    await db.commit()
    await db.refresh(application)
    return application


async def get_candidate_applications(
    db: AsyncSession,
    candidate_id: UUID,
    limit: int = 20,
    offset: int = 0
) -> list[Application]:
    stmt = (
        select(Application)
        .options(
            joinedload(Application.job),
            selectinload(Application.status_history)
        )
        .where(Application.candidate_id == candidate_id)
        .order_by(Application.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_job_applications(
    db: AsyncSession,
    job_id: UUID,
    current_user: User,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0
) -> list[Application]:
    # Check recruiter ownership of the company posting this job
    if current_user.role == "recruiter":
        chk_stmt = (
            select(Job)
            .join(Company, Job.company_id == Company.id)
            .where(Job.id == job_id, Company.recruiter_id == current_user.id)
        )
        chk_res = await db.execute(chk_stmt)
        if not chk_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or access denied"
            )

    stmt = (
        select(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
            selectinload(Application.status_history)
        )
        .where(Application.job_id == job_id)
    )
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)

    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_application_by_id(
    db: AsyncSession,
    application_id: UUID,
    current_user: User
) -> Application:
    stmt = (
        select(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
            selectinload(Application.status_history)
        )
        .where(Application.id == application_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    if current_user.role == "candidate":
        if app.candidate_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == "recruiter":
        comp_stmt = select(Company).where(
            Company.id == app.job.company_id,
            Company.recruiter_id == current_user.id
        )
        comp_res = await db.execute(comp_stmt)
        if not comp_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

    return app


async def update_application_status(
    db: AsyncSession,
    application_id: UUID,
    data: ApplicationStatusUpdate,
    current_user: User
) -> Application:
    stmt = (
        select(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
            selectinload(Application.status_history)
        )
        .where(Application.id == application_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Recruiter can only modify applications for their own company's jobs
    if current_user.role == "recruiter":
        comp_stmt = select(Company).where(
            Company.id == app.job.company_id,
            Company.recruiter_id == current_user.id
        )
        comp_res = await db.execute(comp_stmt)
        if not comp_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

    # Validate state transition
    if app.status == data.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is already in '{app.status}' status"
        )

    allowed = VALID_STATUS_TRANSITIONS.get(app.status, set())
    if data.status not in allowed and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{app.status}' to '{data.status}'"
        )

    old_status = app.status
    app.status = data.status

    history = ApplicationStatusHistory(
        application_id=app.id,
        from_status=old_status,
        to_status=data.status,
        changed_by_user_id=current_user.id,
        notes=data.notes
    )
    db.add(history)
    await db.commit()
    await db.refresh(app)
    return app
