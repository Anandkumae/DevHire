import uuid
from decimal import Decimal
from app.models.user import User
from app.models.company import Company
from app.models.job import Job
from app.models.skill import Skill


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
