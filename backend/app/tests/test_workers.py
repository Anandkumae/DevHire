import uuid
import pytest
from app.workers.celery_app import celery_app
from app.workers.email_tasks import (
    send_application_status_updated_email,
    send_application_submitted_email,
    send_interview_invitation_email,
    send_raw_email_task,
)
from app.workers.resume_tasks import process_uploaded_resume_task


def test_celery_task_registration():
    """Verify that all background tasks are properly discovered and registered with Celery."""
    registered = celery_app.tasks.keys()
    assert "app.workers.email_tasks.send_raw_email_task" in registered
    assert "app.workers.email_tasks.send_application_submitted_email" in registered
    assert "app.workers.email_tasks.send_application_status_updated_email" in registered
    assert "app.workers.email_tasks.send_interview_invitation_email" in registered
    assert "app.workers.resume_tasks.process_uploaded_resume_task" in registered


def test_send_raw_email_task():
    """Verify raw email delivery task returns valid delivery receipt."""
    receipt = send_raw_email_task(
        recipient_email="candidate@example.com",
        subject="Welcome to DevHire",
        body="Thank you for joining our platform."
    )
    assert receipt["recipient"] == "candidate@example.com"
    assert receipt["subject"] == "Welcome to DevHire"
    assert receipt["status"] == "delivered"


def test_send_application_submitted_email():
    """Verify application confirmation email generation and formatting."""
    receipt = send_application_submitted_email(
        candidate_email="arjun@example.com",
        candidate_name="Arjun Sharma",
        job_title="Senior Backend Engineer",
        company_name="TechCorp Labs"
    )
    assert receipt["recipient"] == "arjun@example.com"
    assert "Application Received: Senior Backend Engineer at TechCorp Labs" in receipt["subject"]
    assert receipt["status"] == "delivered"


def test_send_application_status_updated_email():
    """Verify status update notification task with recruiter notes."""
    receipt = send_application_status_updated_email(
        candidate_email="arjun@example.com",
        candidate_name="Arjun Sharma",
        job_title="Senior Backend Engineer",
        new_status="shortlisted",
        notes="Candidate passed coding assessment with 100% score."
    )
    assert receipt["recipient"] == "arjun@example.com"
    assert "Shortlisted" in receipt["subject"]
    assert receipt["status"] == "delivered"


def test_send_interview_invitation_email():
    """Verify interview invitation task with round details and meeting link."""
    receipt = send_interview_invitation_email(
        candidate_email="arjun@example.com",
        candidate_name="Arjun Sharma",
        round_name="System Design Round 1",
        scheduled_at_str="2026-11-05 15:00 UTC",
        meeting_link="https://meet.google.com/xyz-uvwx-rst"
    )
    assert receipt["recipient"] == "arjun@example.com"
    assert "System Design Round 1" in receipt["subject"]
    assert receipt["status"] == "delivered"


def test_process_uploaded_resume_task():
    """Verify background resume indexing and parsing preparation task."""
    resume_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    result = process_uploaded_resume_task(
        resume_id=resume_id,
        candidate_id=candidate_id,
        file_name="arjun_resume.pdf",
        file_size_bytes=1024500
    )
    assert result["resume_id"] == resume_id
    assert result["file_name"] == "arjun_resume.pdf"
    assert result["status"] == "processed"
