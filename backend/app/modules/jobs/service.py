from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Company, Job, Skill, User
from app.modules.jobs.schemas import JobCreate, JobUpdate


async def create_job(
    db: AsyncSession,
    data: JobCreate,
    current_user: User
) -> Job:
    # Recruiters can only create jobs under their own registered company
    if current_user.role == "recruiter":
        result = await db.execute(
            select(Company).where(Company.recruiter_id == current_user.id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Register a company before creating jobs"
            )
        company_id = company.id
    else:
        # Admins must explicitly specify the company
        if not data.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin must provide company_id"
            )
        comp_res = await db.execute(
            select(Company).where(Company.id == data.company_id)
        )
        if not comp_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified company not found"
            )
        company_id = data.company_id

    # Resolve or create skills
    skill_objs: list[Skill] = []
    if data.skills:
        for s_name in data.skills:
            clean_name = s_name.strip()
            if not clean_name:
                continue
            res = await db.execute(select(Skill).where(Skill.name.ilike(clean_name)))
            skill = res.scalar_one_or_none()
            if not skill:
                skill = Skill(name=clean_name)
                db.add(skill)
                await db.flush()
            skill_objs.append(skill)

    job = Job(
        company_id=company_id,
        title=data.title,
        description=data.description,
        location=data.location,
        employment_type=data.employment_type,
        experience_level=data.experience_level,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        status=data.status,
        skills=skill_objs
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_jobs(
    db: AsyncSession,
    search: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    experience_level: str | None = None,
    min_salary: Decimal | None = None,
    max_salary: Decimal | None = None,
    limit: int = 20,
    offset: int = 0
) -> list[Job]:
    # Candidates and public can only view published jobs
    stmt = (
        select(Job)
        .options(selectinload(Job.skills))
        .where(Job.status == "published")
    )

    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(search_filter),
                Job.description.ilike(search_filter)
            )
        )

    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))

    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)

    if experience_level:
        stmt = stmt.where(Job.experience_level == experience_level)

    # Salary filtering uses overlapping salary ranges
    if min_salary is not None:
        stmt = stmt.where(
            or_(
                Job.salary_max.is_(None),
                Job.salary_max >= min_salary
            )
        )

    if max_salary is not None:
        stmt = stmt.where(
            or_(
                Job.salary_min.is_(None),
                Job.salary_min <= max_salary
            )
        )

    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_job(
    db: AsyncSession,
    job_id: UUID,
    current_user: User | None = None
) -> Job:
    stmt = (
        select(Job)
        .options(selectinload(Job.skills))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Public users and candidates can only view published jobs
    if job.status != "published":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        if current_user.role == "recruiter":
            # Check if this recruiter owns the company that posted this job
            comp_res = await db.execute(
                select(Company).where(
                    Company.id == job.company_id,
                    Company.recruiter_id == current_user.id
                )
            )
            if not comp_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
        elif current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

    return job


async def get_job_with_ownership_check(
    db: AsyncSession,
    job_id: UUID,
    current_user: User
) -> Job:
    """Verifies that the job exists and belongs to the recruiter's company (or user is admin)."""
    if current_user.role == "admin":
        stmt = (
            select(Job)
            .options(selectinload(Job.skills))
            .where(Job.id == job_id)
        )
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return job

    # Recruiters must own the company linked to the job
    stmt = (
        select(Job)
        .options(selectinload(Job.skills))
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id, Company.recruiter_id == current_user.id)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job


async def update_job(
    db: AsyncSession,
    job_id: UUID,
    data: JobUpdate,
    current_user: User
) -> Job:
    job = await get_job_with_ownership_check(db, job_id, current_user)
    update_dict = data.model_dump(exclude_unset=True)

    # Check effective salary range consistency
    new_min = update_dict.get("salary_min", job.salary_min)
    new_max = update_dict.get("salary_max", job.salary_max)
    if new_min is not None and new_max is not None and new_min > new_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="salary_min cannot exceed salary_max"
        )

    # Update skills if provided
    if "skills" in update_dict and update_dict["skills"] is not None:
        skill_objs: list[Skill] = []
        for s_name in update_dict["skills"]:
            clean_name = s_name.strip()
            if not clean_name:
                continue
            res = await db.execute(select(Skill).where(Skill.name.ilike(clean_name)))
            skill = res.scalar_one_or_none()
            if not skill:
                skill = Skill(name=clean_name)
                db.add(skill)
                await db.flush()
            skill_objs.append(skill)
        job.skills = skill_objs
        del update_dict["skills"]

    for field, value in update_dict.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


async def close_job(
    db: AsyncSession,
    job_id: UUID,
    current_user: User
) -> Job:
    job = await get_job_with_ownership_check(db, job_id, current_user)
    job.status = "closed"
    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(
    db: AsyncSession,
    job_id: UUID,
    current_user: User
) -> dict:
    job = await get_job_with_ownership_check(db, job_id, current_user)
    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted successfully"}
