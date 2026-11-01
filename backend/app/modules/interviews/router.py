from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user, require_roles
from app.modules.interviews.schemas import (
    InterviewCreate,
    InterviewFeedbackCreate,
    InterviewFeedbackResponse,
    InterviewReschedule,
    InterviewResponse,
)
from app.modules.interviews.service import (
    cancel_interview,
    get_application_interviews,
    get_candidate_interviews,
    get_interview_by_id,
    reschedule_interview,
    schedule_interview,
    submit_interview_feedback,
)

router = APIRouter(
    prefix="/interviews",
    tags=["Interviews"]
)


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Interview (Recruiter/Admin)"
)
async def schedule_new_interview(
    data: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await schedule_interview(db, data, current_user)


@router.patch(
    "/{interview_id}/reschedule",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule Interview"
)
async def reschedule(
    interview_id: UUID,
    data: InterviewReschedule,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await reschedule_interview(db, interview_id, data, current_user)


@router.patch(
    "/{interview_id}/cancel",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Interview"
)
async def cancel(
    interview_id: UUID,
    reason: str | None = Query(None, description="Reason for cancellation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await cancel_interview(db, interview_id, current_user, reason=reason)


@router.post(
    "/{interview_id}/feedback",
    response_model=InterviewFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Interview Feedback & Score Rubric"
)
async def submit_feedback(
    interview_id: UUID,
    data: InterviewFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("recruiter", "admin"))
):
    return await submit_interview_feedback(db, interview_id, data, current_user)


@router.get(
    "/my-interviews",
    response_model=list[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authenticated Candidate's Scheduled Interviews"
)
async def list_my_interviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await get_candidate_interviews(db, current_user.id)


@router.get(
    "/application/{application_id}",
    response_model=list[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Interviews for an Application"
)
async def list_interviews_for_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_application_interviews(db, application_id, current_user)


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Interview Details and Evaluation Rubric"
)
async def get_interview(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_interview_by_id(db, interview_id, current_user)

