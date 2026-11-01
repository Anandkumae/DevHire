import uuid
from datetime import datetime
from decimal import Decimal
from app.models.user import User
from app.models.company import Company
from app.models.job import Job
from app.models.skill import Skill
from app.models.application import Application, ApplicationStatusHistory
from app.models.resume import Resume
from app.models.interview import Interview, InterviewFeedback
from app.models.notification import Notification
from app.models.application_match import ApplicationMatchScore


def test_user_model_initialization():
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Anand Kumar",
        email="anand@example.com",
        password_hash="argon2_hashed_secret",
        role="candidate"
    )

    assert user.id == user_id
    assert user.full_name == "Anand Kumar"
    assert user.email == "anand@example.com"
    assert user.role == "candidate"
    assert repr(user) == "<User anand@example.com (candidate)>"


def test_company_model_initialization():
    company_id = uuid.uuid4()
    recruiter_id = uuid.uuid4()
    company = Company(
        id=company_id,
        name="TechCorp India",
        description="A premier engineering consultancy",
        website="https://techcorp.in",
        industry="Information Technology",
        recruiter_id=recruiter_id
    )

    assert company.id == company_id
    assert company.name == "TechCorp India"
    assert company.recruiter_id == recruiter_id
    assert repr(company) == f"<Company TechCorp India recruiter_id={recruiter_id}>"


def test_skill_model_initialization():
    skill_id = uuid.uuid4()
    skill = Skill(
        id=skill_id,
        name="Python"
    )

    assert skill.id == skill_id
    assert skill.name == "Python"
    assert repr(skill) == "<Skill Python>"


def test_job_model_initialization():
    job_id = uuid.uuid4()
    company_id = uuid.uuid4()
    job = Job(
        id=job_id,
        company_id=company_id,
        title="Senior Backend Engineer",
        description="Design and scale backend services in FastAPI.",
        location="Bangalore (Hybrid)",
        employment_type="full-time",
        salary_min=Decimal("1800000.00"),
        salary_max=Decimal("2600000.00"),
        experience_level="senior",
        status="published"
    )

    assert job.id == job_id
    assert job.company_id == company_id
    assert job.title == "Senior Backend Engineer"
    assert job.status == "published"
    assert job.salary_min == Decimal("1800000.00")
    assert repr(job) == f"<Job Senior Backend Engineer company_id={company_id} status=published>"


def test_application_models_initialization():
    app_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()

    application = Application(
        id=app_id,
        candidate_id=candidate_id,
        job_id=job_id,
        cover_letter="Passionate backend engineer with 2 years of experience.",
        resume_url="https://s3.amazonaws.com/devhire-resumes/test_resume.pdf",
        status="applied"
    )

    assert application.id == app_id
    assert application.candidate_id == candidate_id
    assert application.job_id == job_id
    assert application.status == "applied"
    assert repr(application) == f"<Application candidate_id={candidate_id} job_id={job_id} status=applied>"

    history_id = uuid.uuid4()
    history = ApplicationStatusHistory(
        id=history_id,
        application_id=app_id,
        from_status="applied",
        to_status="under_review",
        changed_by_user_id=candidate_id,
        notes="Candidate moved to under review by recruiter."
    )

    assert history.id == history_id
    assert history.application_id == app_id
    assert history.from_status == "applied"
    assert history.to_status == "under_review"
    assert repr(history) == f"<ApplicationStatusHistory app_id={app_id} applied->under_review>"


def test_resume_model_initialization():
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    resume = Resume(
        id=resume_id,
        candidate_id=candidate_id,
        file_name="anand_kumar_resume.pdf",
        s3_key="resumes/cand_123/anand_kumar_resume.pdf",
        file_size_bytes=1048576,
        content_type="application/pdf",
        is_primary=True
    )

    assert resume.id == resume_id
    assert resume.candidate_id == candidate_id
    assert resume.file_name == "anand_kumar_resume.pdf"
    assert resume.file_size_bytes == 1048576
    assert resume.content_type == "application/pdf"
    assert resume.is_primary is True
    assert repr(resume) == f"<Resume candidate_id={candidate_id} file_name=anand_kumar_resume.pdf primary=True>"


def test_interview_models_initialization():
    interview_id = uuid.uuid4()
    app_id = uuid.uuid4()
    interviewer_id = uuid.uuid4()
    scheduled_time = datetime.now()

    interview = Interview(
        id=interview_id,
        application_id=app_id,
        round_name="Technical Round 1",
        interview_type="video",
        scheduled_at=scheduled_time,
        duration_minutes=60,
        meeting_link="https://meet.google.com/abc-defg-hij",
        interviewer_id=interviewer_id,
        status="scheduled"
    )

    assert interview.id == interview_id
    assert interview.application_id == app_id
    assert interview.round_name == "Technical Round 1"
    assert interview.duration_minutes == 60
    assert repr(interview) == f"<Interview id={interview_id} round=Technical Round 1 status=scheduled>"

    feedback_id = uuid.uuid4()
    feedback = InterviewFeedback(
        id=feedback_id,
        interview_id=interview_id,
        interviewer_id=interviewer_id,
        rating=5,
        technical_skills="Superb understanding of async Python and PostgreSQL indexing.",
        soft_skills="Clear communicator and team-oriented.",
        overall_feedback="Strong recommendation for hire.",
        recommendation="strong_hire"
    )

    assert feedback.id == feedback_id
    assert feedback.interview_id == interview_id
    assert feedback.rating == 5
    assert feedback.recommendation == "strong_hire"
    assert repr(feedback) == f"<InterviewFeedback interview_id={interview_id} rating=5 recommendation=strong_hire>"


def test_notification_model_initialization():
    notif_id = uuid.uuid4()
    user_id = uuid.uuid4()

    notif = Notification(
        id=notif_id,
        user_id=user_id,
        type="application_received",
        title="New Application Received",
        message="A new candidate applied to your posted job.",
        is_read=False
    )

    assert notif.id == notif_id
    assert notif.user_id == user_id
    assert notif.type == "application_received"
    assert notif.is_read is False
    assert repr(notif) == f"<Notification user_id={user_id} type=application_received is_read=False>"


def test_application_match_model_initialization():
    match_id = uuid.uuid4()
    app_id = uuid.uuid4()

    match = ApplicationMatchScore(
        id=match_id,
        application_id=app_id,
        overall_score=88.5,
        skills_score=90.0,
        semantic_score=85.0,
        experience_score=100.0,
        matching_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_skills=["Docker"],
        strengths=["Matched 3 core skills", "Senior level confirmed"],
        gap_analysis=["Missing Docker"],
        summary="Strong Match (88.5%)"
    )

    assert match.id == match_id
    assert match.application_id == app_id
    assert match.overall_score == 88.5
    assert match.skills_score == 90.0
    assert "Python" in match.matching_skills
    assert "Docker" in match.missing_skills
    assert repr(match) == f"<ApplicationMatchScore app_id={app_id} score=88.5%>"

