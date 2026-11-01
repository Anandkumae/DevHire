import uuid
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import storage_service
from app.models import Application, Company, Job, Resume, User
from app.modules.resumes.schemas import (
    PresignedUploadRequest,
    PresignedUploadResponse,
    ResumeResponse,
)


def validate_resume_file(file_name: str, file_bytes: bytes, content_type: str | None = None) -> None:
    """Strictly validates resume file extension, size, MIME type, and magic header."""
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are allowed"
        )

    if content_type and content_type not in settings.RESUME_ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{content_type}'. Must be application/pdf"
        )

    if len(file_bytes) > settings.RESUME_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.RESUME_MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Magic byte validation for PDF files
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid PDF file header"
        )


async def upload_resume(
    db: AsyncSession,
    file_name: str,
    file_bytes: bytes,
    content_type: str,
    current_user: User
) -> ResumeResponse:
    validate_resume_file(file_name, file_bytes, content_type)

    # Unset previous primary resumes for this candidate
    await db.execute(
        update(Resume)
        .where(Resume.candidate_id == current_user.id)
        .values(is_primary=False)
    )

    clean_name = file_name.replace(" ", "_")
    s3_key = f"resumes/{current_user.id}/{uuid.uuid4().hex}_{clean_name}"

    # Upload to S3 storage (or dev fallback)
    storage_service.upload_file(file_bytes, s3_key, content_type="application/pdf")

    resume = Resume(
        candidate_id=current_user.id,
        file_name=clean_name,
        s3_key=s3_key,
        file_size_bytes=len(file_bytes),
        content_type="application/pdf",
        is_primary=True
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    download_url = storage_service.generate_presigned_download_url(resume.s3_key)

    return ResumeResponse(
        id=resume.id,
        candidate_id=resume.candidate_id,
        file_name=resume.file_name,
        file_size_bytes=resume.file_size_bytes,
        content_type=resume.content_type,
        is_primary=resume.is_primary,
        download_url=download_url,
        created_at=resume.created_at
    )


async def create_presigned_upload(
    db: AsyncSession,
    data: PresignedUploadRequest,
    current_user: User
) -> PresignedUploadResponse:
    if not data.file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are allowed"
        )

    # Unset previous primary resumes
    await db.execute(
        update(Resume)
        .where(Resume.candidate_id == current_user.id)
        .values(is_primary=False)
    )

    clean_name = data.file_name.replace(" ", "_")
    s3_key = f"resumes/{current_user.id}/{uuid.uuid4().hex}_{clean_name}"

    upload_info = storage_service.generate_presigned_upload_url(
        s3_key=s3_key,
        content_type=data.content_type,
        expires_in=3600
    )

    resume = Resume(
        candidate_id=current_user.id,
        file_name=clean_name,
        s3_key=s3_key,
        file_size_bytes=data.file_size_bytes,
        content_type=data.content_type,
        is_primary=True
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return PresignedUploadResponse(
        resume_id=resume.id,
        s3_key=s3_key,
        upload_url=upload_info["upload_url"],
        method=upload_info["method"],
        headers=upload_info["headers"],
        expires_in=upload_info["expires_in"]
    )


async def get_candidate_resumes(
    db: AsyncSession,
    candidate_id: UUID
) -> list[ResumeResponse]:
    stmt = (
        select(Resume)
        .where(Resume.candidate_id == candidate_id)
        .order_by(Resume.created_at.desc())
    )
    result = await db.execute(stmt)
    resumes = list(result.scalars().all())

    responses: list[ResumeResponse] = []
    for r in resumes:
        download_url = storage_service.generate_presigned_download_url(r.s3_key)
        responses.append(
            ResumeResponse(
                id=r.id,
                candidate_id=r.candidate_id,
                file_name=r.file_name,
                file_size_bytes=r.file_size_bytes,
                content_type=r.content_type,
                is_primary=r.is_primary,
                download_url=download_url,
                created_at=r.created_at
            )
        )
    return responses


async def get_resume_by_id(
    db: AsyncSession,
    resume_id: UUID,
    current_user: User
) -> ResumeResponse:
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    # Authorization check
    if current_user.role == "candidate":
        if resume.candidate_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resume"
            )
    elif current_user.role == "recruiter":
        # Check if candidate applied to any job owned by recruiter's company
        chk_stmt = (
            select(Application)
            .join(Job, Application.job_id == Job.id)
            .join(Company, Job.company_id == Company.id)
            .where(
                Application.candidate_id == resume.candidate_id,
                Company.recruiter_id == current_user.id
            )
        )
        chk_res = await db.execute(chk_stmt)
        if not chk_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view resumes of candidates who applied to your company"
            )

    download_url = storage_service.generate_presigned_download_url(resume.s3_key)
    return ResumeResponse(
        id=resume.id,
        candidate_id=resume.candidate_id,
        file_name=resume.file_name,
        file_size_bytes=resume.file_size_bytes,
        content_type=resume.content_type,
        is_primary=resume.is_primary,
        download_url=download_url,
        created_at=resume.created_at
    )


async def delete_resume(
    db: AsyncSession,
    resume_id: UUID,
    current_user: User
) -> dict:
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    if current_user.role != "admin" and resume.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this resume"
        )

    was_primary = resume.is_primary
    cand_id = resume.candidate_id

    # Remove from storage and DB
    storage_service.delete_file(resume.s3_key)
    await db.delete(resume)
    await db.flush()

    # If it was primary, promote the most recently uploaded remaining resume
    if was_primary:
        remaining_stmt = (
            select(Resume)
            .where(Resume.candidate_id == cand_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        remaining_res = await db.execute(remaining_stmt)
        newest = remaining_res.scalar_one_or_none()
        if newest:
            newest.is_primary = True

    await db.commit()
    return {"message": "Resume deleted successfully"}


async def set_primary_resume(
    db: AsyncSession,
    resume_id: UUID,
    current_user: User
) -> ResumeResponse:
    stmt = select(Resume).where(
        Resume.id == resume_id,
        Resume.candidate_id == current_user.id
    )
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    # Unset other primaries
    await db.execute(
        update(Resume)
        .where(Resume.candidate_id == current_user.id)
        .values(is_primary=False)
    )
    resume.is_primary = True
    await db.commit()
    await db.refresh(resume)

    download_url = storage_service.generate_presigned_download_url(resume.s3_key)
    return ResumeResponse(
        id=resume.id,
        candidate_id=resume.candidate_id,
        file_name=resume.file_name,
        file_size_bytes=resume.file_size_bytes,
        content_type=resume.content_type,
        is_primary=resume.is_primary,
        download_url=download_url,
        created_at=resume.created_at
    )

