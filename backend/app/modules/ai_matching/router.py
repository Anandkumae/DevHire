from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.ai_matching.schemas import (
    ApplicationMatchResponse,
    RankedCandidateResponse
)
from app.modules.ai_matching import service

router = APIRouter(prefix="", tags=["AI Resume Matching"])


@router.get(
    "/jobs/{job_id}/ranked-candidates",
    response_model=List[RankedCandidateResponse],
    summary="Get candidates ranked by AI resume match score"
)
async def get_job_ranked_candidates(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await service.get_job_ranked_candidates(
        db=db,
        job_id=job_id,
        current_user=current_user
    )


@router.get(
    "/applications/{application_id}/match-score",
    response_model=ApplicationMatchResponse,
    summary="Get explainable AI match analysis for an application"
)
async def get_application_match_score(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await service.get_application_match_score(
        db=db,
        application_id=application_id,
        current_user=current_user
    )


@router.post(
    "/applications/{application_id}/recompute-match",
    response_model=ApplicationMatchResponse,
    summary="Recompute AI resume match score for an application"
)
async def recompute_application_match(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify authorization
    await service.get_application_match_score(
        db=db,
        application_id=application_id,
        current_user=current_user
    )
    return await service.compute_application_match(
        db=db,
        application_id=application_id
    )

