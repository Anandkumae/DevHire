import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from sqlalchemy import update

from app.database.session import AsyncSessionLocal
from app.main import app
from app.models import User
from app.core.ai_matching import (
    analyze_resume_for_job,
    build_skill_pattern,
    compute_semantic_similarity,
    evaluate_experience_level,
    extract_text_from_pdf,
    match_skills,
    normalize_text,
)
from app.workers.resume_tasks import calculate_application_match_task


async def promote_user_role(email: str, role: str):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.email == email).values(role=role)
        )
        await session.commit()


def create_minimal_pdf_bytes() -> bytes:
    """Generate a minimal valid in-memory PDF containing text for test verification."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_core_ai_text_and_skills_matching():
    # 1. Text normalization
    raw_text = "  Senior   Python   Developer \n\n with FastAPI \t and AWS  "
    assert normalize_text(raw_text) == "Senior Python Developer with FastAPI and AWS"

    # 2. Skill matching with edge cases (C++, .NET, Node.js)
    resume = "Expert in C++, Python, .NET Core, Node.js, and Docker with 6 years experience."
    target_skills = ["Python", "C++", ".NET", "Node.js", "Docker", "Kubernetes", "Ruby"]

    matching, missing, score = match_skills(resume, target_skills)
    assert "Python" in matching
    assert "C++" in matching
    assert ".NET" in matching
    assert "Node.js" in matching
    assert "Docker" in matching
    assert "Kubernetes" in missing
    assert "Ruby" in missing
    assert len(matching) == 5
    assert len(missing) == 2
    assert score == round((5 / 7) * 100.0, 1)


def test_core_ai_semantic_similarity():
    resume_text = "Experienced backend software engineer specializing in Python, FastAPI, PostgreSQL, asynchronous systems and RESTful APIs."
    job_desc = "Seeking backend engineer to build scalable REST APIs with Python and PostgreSQL."
    irrelevant_job = "Looking for head chef with experience in pastry, baking, kitchen management and french cuisine."

    sim_relevant = compute_semantic_similarity(resume_text, "Backend Engineer", job_desc, ["Python", "FastAPI"])
    sim_irrelevant = compute_semantic_similarity(resume_text, "Executive Pastry Chef", irrelevant_job, ["Baking", "Pastry"])

    assert sim_relevant > sim_irrelevant
    assert sim_relevant >= 50.0
    assert sim_irrelevant == 0.0


def test_core_ai_experience_evaluation():
    senior_resume = "Principal Software Architect with 8+ years experience leading distributed systems teams."
    score, remarks = evaluate_experience_level(senior_resume, "lead")
    assert score == 100.0
    assert any("leadership" in r.lower() or "lead" in r.lower() for r in remarks)

    junior_resume = "Junior developer with 1 year internship experience in frontend development."
    score_jr, remarks_jr = evaluate_experience_level(junior_resume, "senior")
    assert score_jr <= 60.0


def test_core_ai_comprehensive_analysis():
    resume = "Senior Python Developer with 5+ years building backend microservices with FastAPI, PostgreSQL, and Docker."
    analysis = analyze_resume_for_job(
        resume_text=resume,
        job_title="Senior Python Backend Engineer",
        job_description="We need a senior backend engineer to build high throughput APIs using FastAPI, Docker, PostgreSQL, and Kubernetes.",
        job_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
        experience_level="senior"
    )

    assert analysis["overall_score"] >= 65.0
    assert analysis["skills_score"] == 80.0
    assert "Python" in analysis["matching_skills"]
    assert "Kubernetes" in analysis["missing_skills"]
    assert len(analysis["strengths"]) > 0
    assert len(analysis["gap_analysis"]) > 0
    assert "Match" in analysis["summary"]


@pytest.mark.anyio
async def test_ai_matching_full_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Recruiter and Candidate
        tag = uuid.uuid4().hex[:8]
        recruiter_email = f"ai_recruiter_{tag}@techcorp.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": recruiter_email,
                "password": "Password123!",
                "full_name": "AI Recruiter"
            }
        )
        await promote_user_role(recruiter_email, "recruiter")

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": recruiter_email, "password": "Password123!"}
        )
        recruiter_token = login_res.json()["access_token"]
        recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

        candidate_email = f"ai_cand_{tag}@gmail.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": candidate_email,
                "password": "Password123!",
                "full_name": "DevHire Candidate"
            }
        )
        cand_login = await client.post(
            "/api/v1/auth/login",
            json={"email": candidate_email, "password": "Password123!"}
        )
        candidate_token = cand_login.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

        # 2. Recruiter creates company and publishes a job with required skills
        await client.post(
            "/api/v1/companies",
            headers=recruiter_headers,
            json={"name": f"AI Cloud Innovations {tag}", "industry": "Technology"}
        )

        job_res = await client.post(
            "/api/v1/jobs",
            headers=recruiter_headers,
            json={
                "title": "Senior Backend AI Engineer",
                "description": "Looking for senior engineer skilled in Python, FastAPI, Docker, and PostgreSQL to build ML pipelines.",
                "location": "Bengaluru",
                "employment_type": "full_time",
                "experience_level": "senior",
                "status": "published"
            }
        )
        assert job_res.status_code == 201
        job_id = job_res.json()["id"]

        # 3. Candidate applies with rich cover letter
        app_res = await client.post(
            "/api/v1/applications",
            headers=candidate_headers,
            json={
                "job_id": job_id,
                "cover_letter": "I have 6 years of senior engineering experience specializing in Python, FastAPI, and Docker for scalable services."
            }
        )
        assert app_res.status_code == 201
        application_id = app_res.json()["id"]

        # 4. Candidate fetches their match score
        score_res = await client.get(
            f"/api/v1/applications/{application_id}/match-score",
            headers=candidate_headers
        )
        assert score_res.status_code == 200
        score_data = score_res.json()
        assert score_data["application_id"] == application_id
        assert "overall_score" in score_data
        assert score_data["overall_score"] > 0
        assert "strengths" in score_data
        assert "gap_analysis" in score_data
        assert "summary" in score_data

        # 5. Recruiter retrieves ranked candidates for the job
        ranked_res = await client.get(
            f"/api/v1/jobs/{job_id}/ranked-candidates",
            headers=recruiter_headers
        )
        assert ranked_res.status_code == 200
        ranked_candidates = ranked_res.json()
        assert len(ranked_candidates) == 1
        assert ranked_candidates[0]["application_id"] == application_id
        assert ranked_candidates[0]["overall_score"] == score_data["overall_score"]

        # 6. Recompute match score
        recompute_res = await client.post(
            f"/api/v1/applications/{application_id}/recompute-match",
            headers=recruiter_headers
        )
        assert recompute_res.status_code == 200
        assert recompute_res.json()["application_id"] == application_id

        # 7. Unauthorized recruiter access check
        other_recruiter_email = f"competing_{tag}@other.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": other_recruiter_email,
                "password": "Password123!",
                "full_name": "Other Recruiter"
            }
        )
        await promote_user_role(other_recruiter_email, "recruiter")

        other_login = await client.post(
            "/api/v1/auth/login",
            json={"email": other_recruiter_email, "password": "Password123!"}
        )
        other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

        unauthorized_res = await client.get(
            f"/api/v1/jobs/{job_id}/ranked-candidates",
            headers=other_headers
        )
        assert unauthorized_res.status_code == 403

        # 8. Test Celery worker task execution directly
        task_result = calculate_application_match_task(str(application_id))
        assert task_result["application_id"] == str(application_id)
        assert "overall_score" in task_result
