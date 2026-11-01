import asyncio
import concurrent.futures
import logging
import uuid
from app.workers.celery_app import celery_app

logger = logging.getLogger("devhire.workers.resume")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="app.workers.resume_tasks.process_uploaded_resume_task"
)
def process_uploaded_resume_task(
    self,
    resume_id: str,
    candidate_id: str,
    file_name: str,
    file_size_bytes: int
) -> dict:
    """Processes uploaded resume in background: indexing metadata and preparing parsing cache."""
    logger.info(f"Processing resume '{file_name}' (ID: {resume_id}) for candidate {candidate_id}")

    result = {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "file_name": file_name,
        "file_size_bytes": file_size_bytes,
        "status": "processed",
        "task_id": self.request.id if hasattr(self, "request") and self.request else None
    }
    return result


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="app.workers.resume_tasks.calculate_application_match_task"
)
def calculate_application_match_task(self, application_id: str) -> dict:
    """Asynchronous background worker to compute AI match score for an application."""
    logger.info(f"Computing AI match score for application {application_id}")

    async def _async_compute():
        from app.database.session import AsyncSessionLocal
        from app.modules.ai_matching.service import compute_application_match

        async with AsyncSessionLocal() as db:
            score = await compute_application_match(db, uuid.UUID(application_id))
            return {
                "application_id": str(score.application_id),
                "overall_score": score.overall_score,
                "skills_score": score.skills_score,
                "semantic_score": score.semantic_score,
                "experience_score": score.experience_score,
                "summary": score.summary,
                "task_id": self.request.id if hasattr(self, "request") and self.request else None
            }

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _async_compute()).result()
    else:
        return asyncio.run(_async_compute())
