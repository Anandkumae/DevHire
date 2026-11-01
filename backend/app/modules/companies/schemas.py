from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    location: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    location: str | None = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    website: str | None
    industry: str | None
    location: str | None
    recruiter_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

