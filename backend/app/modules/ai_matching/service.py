from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.ai_matching import analyze_resume_for_job, extract_text_from_pdf
from app.core.storage import storage_service
from app.models import (
    Application,
    ApplicationMatchScore,
    Company,
    Job,
    Resume,
    User
)
from app.modules.ai_matching.schemas import RankedCandidateResponse


async def compute_application_match(
    db: AsyncSession,
    application_id: UUID
) -> ApplicationMatchScore:
    """Core logic to analyze candidate application against job requirements and persist match score."""
    stmt = (
        select(Application)
        .options(
            joinedload(Application.job).joinedload(Job.company),
            joinedload(Application.job).selectinload(Job.skills),
            joinedload(Application.candidate),
            joinedload(Application.match_score)
        )
        .where(Application.id == application_id)
    )
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    job = application.job
    candidate = application.candidate

    # 1. Retrieve candidate resume text
    resume_text = ""

    # Try fetching candidate's primary or latest resume
    resume_stmt = (
        select(Resume)
        .where(Resume.candidate_id == candidate.id)
        .order_by(desc(Resume.is_primary), desc(Resume.created_at))
        .limit(1)
    )
    resume_res = await db.execute(resume_stmt)
    resume_obj = resume_res.scalar_one_or_none()

    if resume_obj:
        file_bytes = storage_service.read_file_bytes(resume_obj.s3_key)
        if file_bytes:
            resume_text = extract_text_from_pdf(file_bytes)

    # Supplement or fallback to cover letter or candidate profile text
    if not resume_text and application.cover_letter:
        resume_text = application.cover_letter
    elif application.cover_letter:
        resume_text = f"{resume_text}\n\nCover Letter:\n{application.cover_letter}"

    if not resume_text:
        resume_text = f"Candidate: {candidate.full_name} applying for {job.title}"

    # 2. Extract job skills and specifications
    job_skills = [skill.name for skill in job.skills] if job.skills else []
    analysis = analyze_resume_for_job(
        resume_text=resume_text,
        job_title=job.title,
        job_description=job.description,
        job_skills=job_skills,
        experience_level=job.experience_level
    )

    # 3. Save or update match score record
    match_score = application.match_score
    if not match_score:
        score_stmt = select(ApplicationMatchScore).where(ApplicationMatchScore.application_id == application.id)
        score_res = await db.execute(score_stmt)
        match_score = score_res.scalar_one_or_none()

    if match_score:
        match_score.overall_score = analysis["overall_score"]
        match_score.skills_score = analysis["skills_score"]
        match_score.semantic_score = analysis["semantic_score"]
        match_score.experience_score = analysis["experience_score"]
        match_score.matching_skills = analysis["matching_skills"]
        match_score.missing_skills = analysis["missing_skills"]
        match_score.strengths = analysis["strengths"]
        match_score.gap_analysis = analysis["gap_analysis"]
        match_score.summary = analysis["summary"]
    else:
        match_score = ApplicationMatchScore(
            application_id=application.id,
            overall_score=analysis["overall_score"],
            skills_score=analysis["skills_score"],
            semantic_score=analysis["semantic_score"],
            experience_score=analysis["experience_score"],
            matching_skills=analysis["matching_skills"],
            missing_skills=analysis["missing_skills"],
            strengths=analysis["strengths"],
            gap_analysis=analysis["gap_analysis"],
            summary=analysis["summary"]
        )
        db.add(match_score)

    await db.commit()
    await db.refresh(match_score)

    # 4. Trigger real-time notification to recruiter
    try:
        if job.company and job.company.recruiter_id:
            from app.modules.notifications.service import create_and_send_notification
            await create_and_send_notification(
                db=db,
                user_id=job.company.recruiter_id,
                title="AI Resume Analysis Ready",
                message=f"Candidate {candidate.full_name} scored {analysis['overall_score']}% for '{job.title}'.",
                notification_type="resume_matched",
                data={"application_id": str(application.id), "overall_score": analysis["overall_score"]}
            )
    except Exception:
        pass

    return match_score


async def get_application_match_score(
    db: AsyncSession,
    application_id: UUID,
    current_user: User
) -> ApplicationMatchScore:
    """Fetch explainable AI match score with role-based access control."""
    stmt = (
        select(Application)
        .options(
            joinedload(Application.job).joinedload(Job.company),
            joinedload(Application.match_score)
        )
        .where(Application.id == application_id)
    )
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Role authorization: Candidate owner, Job recruiter, or Admin
    if current_user.role == "candidate" and application.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this match score"
        )
    elif current_user.role == "recruiter":
        if not application.job.company or application.job.company.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view match scores for other companies' jobs"
            )

    # If not yet analyzed, analyze now
    if not application.match_score:
        return await compute_application_match(db, application.id)

    return application.match_score


async def get_job_ranked_candidates(
    db: AsyncSession,
    job_id: UUID,
    current_user: User
) -> List[RankedCandidateResponse]:
    """Retrieve all applicants for a job, ordered by AI match score."""
    # 1. Verify Job exists and Recruiter ownership
    job_stmt = (
        select(Job)
        .options(joinedload(Job.company))
        .where(Job.id == job_id)
    )
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if current_user.role == "recruiter":
        if not job.company or job.company.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view candidates for this job"
            )

    # 2. Query all applications for this job
    apps_stmt = (
        select(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.match_score)
        )
        .where(Application.job_id == job_id)
    )
    apps_res = await db.execute(apps_stmt)
    applications = apps_res.scalars().all()

    # 3. For any application lacking a match score, compute it
    ranked_list = []
    for app in applications:
        match_score = app.match_score
        if not match_score:
            match_score = await compute_application_match(db, app.id)

        ranked_list.append(
            RankedCandidateResponse(
                application_id=app.id,
                candidate_id=app.candidate.id,
                candidate_name=app.candidate.full_name,
                candidate_email=app.candidate.email,
                status=app.status,
                applied_at=app.created_at,
                overall_score=match_score.overall_score if match_score else 0.0,
                match_score=match_score
            )
        )

    # 4. Sort descending by overall match score
    ranked_list.sort(key=lambda x: x.overall_score or 0.0, reverse=True)
    return ranked_list

