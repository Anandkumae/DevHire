from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "applied",
    "under_review",
    "shortlisted",
    "interview",
    "selected",
    "rejected"
]


class ApplicationCreate(BaseModel):
    job_id: UUID
    cover_letter: str | None = Field(default=None, max_length=2000)
    resume_url: str | None = Field(default=None, max_length=500)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: str | None = Field(default=None, max_length=1000)


class StatusHistoryResponse(BaseModel):
    id: UUID
    application_id: UUID
    from_status: str | None
    to_status: str
    changed_by_user_id: UUID | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobBriefResponse(BaseModel):
    id: UUID
    title: str
    company_id: UUID
    location: str
    employment_type: str

    model_config = ConfigDict(from_attributes=True)


class CandidateBriefResponse(BaseModel):
    id: UUID
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    cover_letter: str | None
    resume_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    job: JobBriefResponse | None = None
    candidate: CandidateBriefResponse | None = None
    status_history: list[StatusHistoryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
