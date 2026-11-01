from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ApplicationMatchResponse(BaseModel):
    id: UUID
    application_id: UUID
    overall_score: float = Field(..., ge=0.0, le=100.0)
    skills_score: float = Field(..., ge=0.0, le=100.0)
    semantic_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gap_analysis: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RankedCandidateResponse(BaseModel):
    application_id: UUID
    candidate_id: UUID
    candidate_name: str
    candidate_email: str
    status: str
    applied_at: datetime
    overall_score: Optional[float] = None
    match_score: Optional[ApplicationMatchResponse] = None

    model_config = ConfigDict(from_attributes=True)

