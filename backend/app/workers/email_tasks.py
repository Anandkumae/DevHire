import json
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger("devhire.workers.email")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    retry_jitter=True,
    name="app.workers.email_tasks.send_raw_email_task"
)
def send_raw_email_task(
    self,
    recipient_email: str,
    subject: str,
    body: str
) -> dict:
    """Dispatches email with exponential backoff and automatic retry on network failure."""
    try:
        logger.info(f"Sending email to '{recipient_email}' | Subject: '{subject}'")

        # In a production environment with AWS SES or SendGrid:
        # ses_client.send_email(...)
        # Here we simulate delivery and return delivery receipt
        receipt = {
            "recipient": recipient_email,
            "subject": subject,
            "status": "delivered",
            "task_id": self.request.id,
            "retries": self.request.retries
        }
        return receipt
    except Exception as exc:
        logger.error(f"Failed delivering email to {recipient_email}: {exc}. Retrying...")
        raise self.retry(exc=exc)


@celery_app.task(name="app.workers.email_tasks.send_application_submitted_email")
def send_application_submitted_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    company_name: str
) -> dict:
    subject = f"Application Received: {job_title} at {company_name}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Thank you for applying for the {job_title} position at {company_name} through DevHire.\n"
        f"Our recruiting team will review your application and keep you updated on your application status.\n\n"
        f"Best regards,\n"
        f"The {company_name} Talent Team"
    )
    return send_raw_email_task(candidate_email, subject, body)


@celery_app.task(name="app.workers.email_tasks.send_application_status_updated_email")
def send_application_status_updated_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    new_status: str,
    notes: str | None = None
) -> dict:
    status_label = new_status.replace("_", " ").title()
    subject = f"Application Update: {job_title} ({status_label})"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Your application status for {job_title} has been updated to: {status_label}.\n"
    )
    if notes:
        body += f"\nRecruiter remarks: {notes}\n"
    body += "\nYou can track your application timeline live on DevHire.\n\nBest regards,\nDevHire Recruitment"

    return send_raw_email_task(candidate_email, subject, body)


@celery_app.task(name="app.workers.email_tasks.send_interview_invitation_email")
def send_interview_invitation_email(
    candidate_email: str,
    candidate_name: str,
    round_name: str,
    scheduled_at_str: str,
    meeting_link: str | None = None
) -> dict:
    subject = f"Interview Scheduled: {round_name}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"You have been invited to an interview for the round: {round_name}.\n"
        f"Scheduled Time: {scheduled_at_str}\n"
    )
    if meeting_link:
        body += f"Meeting Link: {meeting_link}\n"
    body += "\nPlease make sure you are in a quiet environment with a working microphone and camera.\n\nBest of luck,\nDevHire Recruiting"

    return send_raw_email_task(candidate_email, subject, body)
