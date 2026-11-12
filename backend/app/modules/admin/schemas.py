from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserListItem(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserStatusUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern="^(candidate|recruiter|admin)$")


class AdminPlatformStats(BaseModel):
    total_users: int
    total_candidates: int
    total_recruiters: int
    total_companies: int
    total_jobs: int
    published_jobs: int
    total_applications: int
    total_interviews: int

