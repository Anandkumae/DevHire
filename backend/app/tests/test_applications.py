import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models import User


async def promote_user_role(email: str, role: str):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.email == email).values(role=role)
        )
        await session.commit()


@pytest.mark.anyio
async def test_applications_full_lifecycle():
    candidate_1_email = f"cand1_{uuid.uuid4().hex[:8]}@example.com"
    candidate_2_email = f"cand2_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_1_email = f"rec1_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_2_email = f"rec2_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register users
        for email in [candidate_1_email, candidate_2_email, recruiter_1_email, recruiter_2_email]:
            res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert res.status_code == 201

        # Promote recruiters
        await promote_user_role(recruiter_1_email, "recruiter")
        await promote_user_role(recruiter_2_email, "recruiter")

        async def get_token(email: str) -> str:
            res = await ac.post("/api/v1/auth/login", json={"email": email, "password": password})
            return res.json()["access_token"]

        cand1_h = {"Authorization": f"Bearer {await get_token(candidate_1_email)}"}
        cand2_h = {"Authorization": f"Bearer {await get_token(candidate_2_email)}"}
        rec1_h = {"Authorization": f"Bearer {await get_token(recruiter_1_email)}"}
        rec2_h = {"Authorization": f"Bearer {await get_token(recruiter_2_email)}"}

        # 1. Recruiter 1 creates company
        comp_res = await ac.post("/api/v1/companies", json={
            "name": f"FinTech Labs {uuid.uuid4().hex[:6]}",
            "description": "Fintech engineering",
            "website": "https://fintechlabs.io",
            "industry": "FinTech",
            "location": "Mumbai, India"
        }, headers=rec1_h)
        assert comp_res.status_code == 201

        # Recruiter 2 creates company
        comp2_res = await ac.post("/api/v1/companies", json={
            "name": f"HealthTech Solutions {uuid.uuid4().hex[:6]}",
            "description": "Healthcare tech",
            "website": "https://healthtech.io",
            "industry": "Health",
            "location": "Delhi, India"
        }, headers=rec2_h)
        assert comp2_res.status_code == 201

        # 2. Recruiter 1 publishes Job A
        job_a_res = await ac.post("/api/v1/jobs", json={
            "title": "Backend Systems Engineer",
            "description": "Build high-throughput payment transaction pipelines using FastAPI.",
            "location": "Mumbai (On-site)",
            "employment_type": "full-time",
            "experience_level": "mid",
            "salary_min": 1800000,
            "salary_max": 2400000,
            "status": "published",
            "skills": ["Python", "FastAPI", "PostgreSQL"]
        }, headers=rec1_h)
        assert job_a_res.status_code == 201
        job_a_id = job_a_res.json()["id"]

        # Recruiter 1 creates Draft Job B
        job_b_res = await ac.post("/api/v1/jobs", json={
            "title": "Draft DevOps Engineer",
            "description": "Manage Kubernetes clusters and AWS infrastructure.",
            "location": "Remote",
            "employment_type": "full-time",
            "experience_level": "senior",
            "status": "draft"
        }, headers=rec1_h)
        assert job_b_res.status_code == 201
        job_b_id = job_b_res.json()["id"]

        # Recruiter 1 creates and closes Job C
        job_c_res = await ac.post("/api/v1/jobs", json={
            "title": "Closed QA Engineer",
            "description": "Automated testing with PyTest and Locust.",
            "location": "Pune",
            "employment_type": "contract",
            "experience_level": "mid",
            "status": "published"
        }, headers=rec1_h)
        assert job_c_res.status_code == 201
        job_c_id = job_c_res.json()["id"]
        close_res = await ac.patch(f"/api/v1/jobs/{job_c_id}/close", headers=rec1_h)
        assert close_res.status_code == 200

        # 3. Recruiter tries to apply for a job -> 403 Forbidden
        rec_apply_res = await ac.post("/api/v1/applications", json={"job_id": job_a_id}, headers=rec1_h)
        assert rec_apply_res.status_code == 403

        # 4. Candidate tries to apply to draft job -> 400 Bad Request
        draft_apply_res = await ac.post("/api/v1/applications", json={"job_id": job_b_id}, headers=cand1_h)
        assert draft_apply_res.status_code == 400
        assert "Cannot apply to a draft job" in draft_apply_res.json()["detail"]

        # 5. Candidate tries to apply to closed job -> 400 Bad Request
        closed_apply_res = await ac.post("/api/v1/applications", json={"job_id": job_c_id}, headers=cand1_h)
        assert closed_apply_res.status_code == 400
        assert "Cannot apply to a closed job" in closed_apply_res.json()["detail"]

        # 6. Candidate 1 successfully applies to Job A -> 201 Created
        apply_payload = {
            "job_id": job_a_id,
            "cover_letter": "I have extensive experience with FastAPI and PostgreSQL transaction management.",
            "resume_url": "https://devhire-bucket.s3.amazonaws.com/resumes/cand1.pdf"
        }
        apply_res = await ac.post("/api/v1/applications", json=apply_payload, headers=cand1_h)
        assert apply_res.status_code == 201
        app_data = apply_res.json()
        assert app_data["status"] == "applied"
        assert app_data["job_id"] == job_a_id
        assert app_data["cover_letter"] == apply_payload["cover_letter"]
        assert len(app_data["status_history"]) == 1
        assert app_data["status_history"][0]["to_status"] == "applied"
        app_id = app_data["id"]

        # 7. Candidate 1 tries to apply again to Job A -> 409 Conflict (Duplicate prevention)
        dup_apply_res = await ac.post("/api/v1/applications", json=apply_payload, headers=cand1_h)
        assert dup_apply_res.status_code == 409
        assert dup_apply_res.json()["detail"] == "You have already applied for this job"

        # 8. Candidate 1 views their submitted applications -> 200 OK
        my_apps_res = await ac.get("/api/v1/applications/me", headers=cand1_h)
        assert my_apps_res.status_code == 200
        my_apps = my_apps_res.json()
        assert any(a["id"] == app_id for a in my_apps)
        assert my_apps[0]["job"]["title"] == "Backend Systems Engineer"

        # 9. Candidate 2 tries to view Candidate 1's application details -> 403 Forbidden
        unauth_cand_res = await ac.get(f"/api/v1/applications/{app_id}", headers=cand2_h)
        assert unauth_cand_res.status_code == 403

        # 10. Candidate 1 views their own application details -> 200 OK
        cand_detail_res = await ac.get(f"/api/v1/applications/{app_id}", headers=cand1_h)
        assert cand_detail_res.status_code == 200
        assert cand_detail_res.json()["id"] == app_id

        # 11. Recruiter 2 (different company) tries to view Job A's applicants -> 404 Not Found
        diff_rec_list_res = await ac.get(f"/api/v1/applications/job/{job_a_id}", headers=rec2_h)
        assert diff_rec_list_res.status_code == 404

        # 12. Recruiter 2 tries to update status of Job A's application -> 404 Not Found
        diff_rec_update_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "under_review"},
            headers=rec2_h
        )
        assert diff_rec_update_res.status_code == 404

        # 13. Recruiter 1 views applicants for Job A -> 200 OK
        rec1_list_res = await ac.get(f"/api/v1/applications/job/{job_a_id}", headers=rec1_h)
        assert rec1_list_res.status_code == 200
        assert any(a["id"] == app_id for a in rec1_list_res.json())

        # 14. Invalid status transition: applied directly to selected -> 400 Bad Request
        bad_transition_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "selected", "notes": "Skipping rounds"},
            headers=rec1_h
        )
        assert bad_transition_res.status_code == 400
        assert "Invalid status transition" in bad_transition_res.json()["detail"]

        # 15. Valid lifecycle transitions:
        # a) applied -> under_review
        step1_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "under_review", "notes": "Initial resume screen passed"},
            headers=rec1_h
        )
        assert step1_res.status_code == 200
        assert step1_res.json()["status"] == "under_review"

        # b) under_review -> shortlisted
        step2_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "shortlisted", "notes": "Shortlisted for technical interviews"},
            headers=rec1_h
        )
        assert step2_res.status_code == 200
        assert step2_res.json()["status"] == "shortlisted"

        # c) shortlisted -> interview
        step3_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "interview", "notes": "Round 1 interview scheduled"},
            headers=rec1_h
        )
        assert step3_res.status_code == 200
        assert step3_res.json()["status"] == "interview"

        # d) interview -> selected
        step4_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "selected", "notes": "Offer extended to candidate"},
            headers=rec1_h
        )
        assert step4_res.status_code == 200
        assert step4_res.json()["status"] == "selected"

        # 16. Verify complete audit trail history
        final_detail_res = await ac.get(f"/api/v1/applications/{app_id}", headers=cand1_h)
        assert final_detail_res.status_code == 200
        history_list = final_detail_res.json()["status_history"]
        assert len(history_list) == 5
        assert history_list[0]["to_status"] == "applied"
        assert history_list[1]["to_status"] == "under_review"
        assert history_list[2]["to_status"] == "shortlisted"
        assert history_list[3]["to_status"] == "interview"
        assert history_list[4]["to_status"] == "selected"
        assert history_list[4]["notes"] == "Offer extended to candidate"

