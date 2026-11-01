import logging
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

    # Simulated async document indexing and preprocessing for AI matching
    result = {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "file_name": file_name,
        "file_size_bytes": file_size_bytes,
        "status": "processed",
        "task_id": self.request.id
    }
    return result
