from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

InterviewStatus = Literal[
    "scheduled",
    "rescheduled",
    "completed",
    "cancelled"
]

InterviewType = Literal[
    "video",
    "phone",
    "in_person"
]

RecommendationType = Literal[
    "strong_hire",
    "hire",
    "no_hire",
    "strong_no_hire"
]


class InterviewCreate(BaseModel):
    application_id: UUID
    round_name: str = Field(min_length=2, max_length=100, description="E.g. Technical Round 1")
    interview_type: InterviewType = "video"
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, gt=0, le=480, description="Duration in minutes")
    meeting_link: str | None = Field(default=None, max_length=500, description="Video link or location")
    interviewer_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class InterviewReschedule(BaseModel):
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    meeting_link: str | None = None
    notes: str | None = None


class InterviewFeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Score from 1 (poor) to 5 (exceptional)")
    technical_skills: str | None = Field(default=None, max_length=2000)
    soft_skills: str | None = Field(default=None, max_length=2000)
    overall_feedback: str = Field(min_length=10, max_length=5000)
    recommendation: RecommendationType


class InterviewFeedbackResponse(BaseModel):
    id: UUID
    interview_id: UUID
    interviewer_id: UUID
    rating: int
    technical_skills: str | None
    soft_skills: str | None
    overall_feedback: str
    recommendation: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewResponse(BaseModel):
    id: UUID
    application_id: UUID
    round_name: str
    interview_type: str
    scheduled_at: datetime
    duration_minutes: int
    meeting_link: str | None
    interviewer_id: UUID | None
    status: str
    notes: str | None
    feedback: InterviewFeedbackResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

