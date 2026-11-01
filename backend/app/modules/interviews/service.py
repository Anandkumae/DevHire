from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    Application,
    ApplicationStatusHistory,
    Company,
    Interview,
    InterviewFeedback,
    Job,
    User,
)
from app.modules.interviews.schemas import (
    InterviewCreate,
    InterviewFeedbackCreate,
    InterviewReschedule,
)


async def check_recruiter_application_access(
    db: AsyncSession,
    application_id: UUID,
    current_user: User
) -> Application:
    stmt = (
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == application_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

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

    return app


async def schedule_interview(
    db: AsyncSession,
    data: InterviewCreate,
    current_user: User
) -> Interview:
    app = await check_recruiter_application_access(db, data.application_id, current_user)

    if app.status in ("rejected", "selected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot schedule interview for a {app.status} application"
        )

    # Transition application status to 'interview' if needed
    if app.status != "interview":
        old_status = app.status
        app.status = "interview"
        history = ApplicationStatusHistory(
            application_id=app.id,
            from_status=old_status,
            to_status="interview",
            changed_by_user_id=current_user.id,
            notes=f"Interview scheduled: {data.round_name}"
        )
        db.add(history)

    interviewer_id = data.interviewer_id or current_user.id

    interview = Interview(
        application_id=data.application_id,
        round_name=data.round_name,
        interview_type=data.interview_type,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        meeting_link=data.meeting_link,
        interviewer_id=interviewer_id,
        status="scheduled",
        notes=data.notes
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return interview


async def reschedule_interview(
    db: AsyncSession,
    interview_id: UUID,
    data: InterviewReschedule,
    current_user: User
) -> Interview:
    stmt = (
        select(Interview)
        .options(joinedload(Interview.application).joinedload(Application.job))
        .where(Interview.id == interview_id)
    )
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    await check_recruiter_application_access(db, interview.application_id, current_user)

    if interview.status in ("cancelled", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule a {interview.status} interview"
        )

    interview.scheduled_at = data.scheduled_at
    if data.duration_minutes is not None:
        interview.duration_minutes = data.duration_minutes
    if data.meeting_link is not None:
        interview.meeting_link = data.meeting_link
    if data.notes is not None:
        interview.notes = data.notes

    interview.status = "rescheduled"
    await db.commit()
    await db.refresh(interview)
    return interview


async def cancel_interview(
    db: AsyncSession,
    interview_id: UUID,
    current_user: User,
    reason: str | None = None
) -> Interview:
    stmt = select(Interview).where(Interview.id == interview_id)
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    await check_recruiter_application_access(db, interview.application_id, current_user)

    if interview.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview is already cancelled")

    interview.status = "cancelled"
    if reason:
        interview.notes = f"{interview.notes or ''}\nCancellation reason: {reason}".strip()

    await db.commit()
    await db.refresh(interview)
    return interview


async def submit_interview_feedback(
    db: AsyncSession,
    interview_id: UUID,
    data: InterviewFeedbackCreate,
    current_user: User
) -> InterviewFeedback:
    stmt = (
        select(Interview)
        .options(joinedload(Interview.feedback))
        .where(Interview.id == interview_id)
    )
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    await check_recruiter_application_access(db, interview.application_id, current_user)

    if interview.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit feedback for a cancelled interview"
        )

    if interview.feedback:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback has already been submitted for this interview"
        )

    feedback = InterviewFeedback(
        interview_id=interview.id,
        interviewer_id=current_user.id,
        rating=data.rating,
        technical_skills=data.technical_skills,
        soft_skills=data.soft_skills,
        overall_feedback=data.overall_feedback,
        recommendation=data.recommendation
    )
    db.add(feedback)
    interview.status = "completed"

    await db.commit()
    await db.refresh(feedback)
    return feedback


async def get_candidate_interviews(
    db: AsyncSession,
    candidate_id: UUID
) -> list[Interview]:
    stmt = (
        select(Interview)
        .join(Application, Interview.application_id == Application.id)
        .where(Application.candidate_id == candidate_id)
        .order_by(Interview.scheduled_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_application_interviews(
    db: AsyncSession,
    application_id: UUID,
    current_user: User
) -> list[Interview]:
    stmt = (
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == application_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if current_user.role == "candidate":
        if app.candidate_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == "recruiter":
        comp_stmt = select(Company).where(
            Company.id == app.job.company_id,
            Company.recruiter_id == current_user.id
        )
        comp_res = await db.execute(comp_stmt)
        if not comp_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    int_stmt = (
        select(Interview)
        .where(Interview.application_id == application_id)
        .order_by(Interview.scheduled_at.asc())
    )
    int_res = await db.execute(int_stmt)
    return list(int_res.scalars().all())


async def get_interview_by_id(
    db: AsyncSession,
    interview_id: UUID,
    current_user: User
) -> Interview:
    stmt = (
        select(Interview)
        .options(
            joinedload(Interview.application).joinedload(Application.job),
            joinedload(Interview.feedback)
        )
        .where(Interview.id == interview_id)
    )
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    app = interview.application
    if current_user.role == "candidate":
        if app.candidate_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == "recruiter":
        comp_stmt = select(Company).where(
            Company.id == app.job.company_id,
            Company.recruiter_id == current_user.id
        )
        comp_res = await db.execute(comp_stmt)
        if not comp_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    return interview

