import os
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user, require_roles
from app.modules.resumes.schemas import (
    PresignedUploadRequest,
    PresignedUploadResponse,
    ResumeResponse,
)
from app.modules.resumes.service import (
    create_presigned_upload,
    delete_resume,
    get_candidate_resumes,
    get_resume_by_id,
    set_primary_resume,
    upload_resume,
)

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Resume (PDF only, max 5MB)"
)
async def upload_candidate_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    file_bytes = await file.read()
    return await upload_resume(
        db=db,
        file_name=file.filename or "resume.pdf",
        file_bytes=file_bytes,
        content_type=file.content_type or "application/pdf",
        current_user=current_user
    )


@router.post(
    "/presigned-upload",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate S3 Presigned Upload URL (Direct Upload)"
)
async def generate_upload_url(
    data: PresignedUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await create_presigned_upload(db, data, current_user)


@router.get(
    "/my-resumes",
    response_model=list[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authenticated Candidate's Resumes"
)
async def list_my_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await get_candidate_resumes(db, current_user.id)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Resume Metadata & Presigned Download URL"
)
async def get_resume(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_resume_by_id(db, resume_id, current_user)


@router.patch(
    "/{resume_id}/primary",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Resume as Primary"
)
async def set_primary(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("candidate"))
):
    return await set_primary_resume(db, resume_id, current_user)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Resume"
)
async def remove_resume(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await delete_resume(db, resume_id, current_user)


@router.get(
    "/download-local/{s3_key:path}",
    summary="Local Storage Download Simulation (Development Fallback)"
)
async def download_local_file(s3_key: str):
    file_path = Path(settings.LOCAL_STORAGE_DIR) / s3_key.replace("/", os.sep)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in local storage"
        )
    return FileResponse(path=file_path, media_type="application/pdf")

