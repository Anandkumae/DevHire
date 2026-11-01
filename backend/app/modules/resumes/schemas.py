from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    file_name: str
    file_size_bytes: int
    content_type: str
    is_primary: bool
    download_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255, description="Original file name")
    file_size_bytes: int = Field(gt=0, le=5 * 1024 * 1024, description="Size in bytes (max 5MB)")
    content_type: str = Field(default="application/pdf", description="MIME type (PDF only)")


class PresignedUploadResponse(BaseModel):
    resume_id: UUID
    s3_key: str
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_in: int
