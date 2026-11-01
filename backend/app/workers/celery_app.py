from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "devhire_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_tasks",
        "app.workers.resume_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.workers.email_tasks.*": {"queue": "emails"},
        "app.workers.resume_tasks.*": {"queue": "resumes"},
    },
    broker_connection_retry_on_startup=True
)

