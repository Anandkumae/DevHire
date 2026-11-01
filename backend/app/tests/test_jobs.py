import uuid
from decimal import Decimal
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
async def test_jobs_full_lifecycle():
    candidate_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_1_email = f"recruiter1_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_no_company_email = f"recruiter_nocomp_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_2_email = f"recruiter2_{uuid.uuid4().hex[:8]}@example.com"
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register test users
        for email in [candidate_email, recruiter_1_email, recruiter_no_company_email, recruiter_2_email, admin_email]:
            reg_res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert reg_res.status_code == 201

        # Promote roles
        await promote_user_role(recruiter_1_email, "recruiter")
        await promote_user_role(recruiter_no_company_email, "recruiter")
        await promote_user_role(recruiter_2_email, "recruiter")
        await promote_user_role(admin_email, "admin")

        # Login helpers
        async def get_token(email: str) -> str:
            res = await ac.post("/api/v1/auth/login", json={"email": email, "password": password})
            return res.json()["access_token"]

        candidate_h = {"Authorization": f"Bearer {await get_token(candidate_email)}"}
        recruiter_1_h = {"Authorization": f"Bearer {await get_token(recruiter_1_email)}"}
        recruiter_no_company_h = {"Authorization": f"Bearer {await get_token(recruiter_no_company_email)}"}
        recruiter_2_h = {"Authorization": f"Bearer {await get_token(recruiter_2_email)}"}
        admin_h = {"Authorization": f"Bearer {await get_token(admin_email)}"}

        # Register companies for recruiter 1 and recruiter 2
        comp1_res = await ac.post("/api/v1/companies", json={
            "name": f"Acme Innovations {uuid.uuid4().hex[:6]}",
            "description": "Tech innovations company",
            "website": "https://acme.io",
            "industry": "IT",
            "location": "Pune, India"
        }, headers=recruiter_1_h)
        assert comp1_res.status_code == 201
        comp1_id = comp1_res.json()["id"]

        comp2_res = await ac.post("/api/v1/companies", json={
            "name": f"Globex Corp {uuid.uuid4().hex[:6]}",
            "description": "Enterprise software",
            "website": "https://globex.com",
            "industry": "Software",
            "location": "Bengaluru, India"
        }, headers=recruiter_2_h)
        assert comp2_res.status_code == 201

        valid_job_payload = {
            "title": "Backend Engineer Intern",
            "description": "Develop scalable backend APIs using Python, FastAPI, PostgreSQL and Redis. Work with the engineering team to improve application performance.",
            "location": "Pune",
            "employment_type": "internship",
            "experience_level": "fresher",
            "salary_min": 15000,
            "salary_max": 25000,
            "status": "published",
            "skills": ["Python", "FastAPI", "PostgreSQL"]
        }

        # 1. Candidate creates job -> 403 Forbidden
        cand_res = await ac.post("/api/v1/jobs", json=valid_job_payload, headers=candidate_h)
        assert cand_res.status_code == 403

        # 2. Recruiter without company creates job -> 400 Bad Request
        no_comp_res = await ac.post("/api/v1/jobs", json=valid_job_payload, headers=recruiter_no_company_h)
        assert no_comp_res.status_code == 400
        assert no_comp_res.json()["detail"] == "Register a company before creating jobs"

        # 3. Invalid salary range (salary_min > salary_max) -> 422 Unprocessable Entity
        invalid_salary_payload = dict(valid_job_payload)
        invalid_salary_payload["salary_min"] = 30000
        invalid_salary_payload["salary_max"] = 20000
        inv_sal_res = await ac.post("/api/v1/jobs", json=invalid_salary_payload, headers=recruiter_1_h)
        assert inv_sal_res.status_code == 422

        # 4. Recruiter creates job -> 201 Created (auto-linked to their company)
        rec1_job_res = await ac.post("/api/v1/jobs", json=valid_job_payload, headers=recruiter_1_h)
        assert rec1_job_res.status_code == 201
        rec1_job = rec1_job_res.json()
        assert rec1_job["company_id"] == comp1_id
        assert rec1_job["title"] == valid_job_payload["title"]
        assert rec1_job["status"] == "published"
        assert len(rec1_job["skills"]) == 3
        job1_id = rec1_job["id"]

        # Recruiter creates a draft job
        draft_payload = dict(valid_job_payload)
        draft_payload["title"] = "Draft Frontend Engineer"
        draft_payload["status"] = "draft"
        draft_res = await ac.post("/api/v1/jobs", json=draft_payload, headers=recruiter_1_h)
        assert draft_res.status_code == 201
        draft_job_id = draft_res.json()["id"]

        # 5. Admin creates job without company ID -> 400 Bad Request
        admin_payload_no_comp = dict(valid_job_payload)
        admin_res_no_comp = await ac.post("/api/v1/jobs", json=admin_payload_no_comp, headers=admin_h)
        assert admin_res_no_comp.status_code == 400
        assert admin_res_no_comp.json()["detail"] == "Admin must provide company_id"

        # 6. Admin creates job with valid company ID -> 201 Created
        admin_payload_valid = dict(valid_job_payload)
        admin_payload_valid["company_id"] = comp1_id
        admin_payload_valid["title"] = "Admin Posted SRE Lead"
        admin_res_valid = await ac.post("/api/v1/jobs", json=admin_payload_valid, headers=admin_h)
        assert admin_res_valid.status_code == 201
        assert admin_res_valid.json()["company_id"] == comp1_id

        # 7. Public browses published jobs -> 200 OK
        browse_res = await ac.get("/api/v1/jobs")
        assert browse_res.status_code == 200
        browse_data = browse_res.json()
        assert any(j["id"] == job1_id for j in browse_data)

        # 8. Public cannot see draft jobs -> Draft excluded from public listing
        assert not any(j["id"] == draft_job_id for j in browse_data)

        # 9. Public tries to fetch draft job directly -> 404 Not Found
        draft_direct_res = await ac.get(f"/api/v1/jobs/{draft_job_id}")
        assert draft_direct_res.status_code == 404

        # 10. Search and filtering: search by keyword and location
        search_res = await ac.get("/api/v1/jobs?search=Backend&location=Pune")
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert any(j["id"] == job1_id for j in search_data)

        # Filter by employment_type, experience_level and salary overlap
        filter_res = await ac.get("/api/v1/jobs?employment_type=internship&experience_level=fresher&min_salary=10000&max_salary=30000")
        assert filter_res.status_code == 200
        assert any(j["id"] == job1_id for j in filter_res.json())

        # Exclude non-matching salary range
        filter_mismatch_res = await ac.get("/api/v1/jobs?min_salary=50000")
        assert filter_mismatch_res.status_code == 200
        assert not any(j["id"] == job1_id for j in filter_mismatch_res.json())

        # 11. Pagination with invalid limit -> 422
        bad_page_res = await ac.get("/api/v1/jobs?limit=0")
        assert bad_page_res.status_code == 422
        bad_page_res2 = await ac.get("/api/v1/jobs?limit=500")
        assert bad_page_res2.status_code == 422

        # Valid pagination
        page_res = await ac.get("/api/v1/jobs?limit=5&offset=0")
        assert page_res.status_code == 200
        assert len(page_res.json()) <= 5

        # 12. Different recruiter tries to update job -> 404 Not Found
        diff_update_res = await ac.patch(
            f"/api/v1/jobs/{job1_id}",
            json={"title": "Hacked Title"},
            headers=recruiter_2_h
        )
        assert diff_update_res.status_code == 404

        # 13. Owner recruiter tries to send explicit null for title -> 422 Unprocessable Entity
        null_title_res = await ac.patch(
            f"/api/v1/jobs/{job1_id}",
            json={"title": None},
            headers=recruiter_1_h
        )
        assert null_title_res.status_code == 422

        # 14. Owner updates job -> 200 OK
        owner_update_res = await ac.patch(
            f"/api/v1/jobs/{job1_id}",
            json={
                "title": "Python Backend Engineer Intern",
                "salary_max": 30000
            },
            headers=recruiter_1_h
        )
        assert owner_update_res.status_code == 200
        assert owner_update_res.json()["title"] == "Python Backend Engineer Intern"
        assert Decimal(str(owner_update_res.json()["salary_max"])) == Decimal("30000")

        # 15. Owner closes job -> 200 OK
        close_res = await ac.patch(f"/api/v1/jobs/{job1_id}/close", headers=recruiter_1_h)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "closed"

        # 16. Closed job disappears from public listing
        browse_after_close = await ac.get("/api/v1/jobs")
        assert not any(j["id"] == job1_id for j in browse_after_close.json())

        # 17. Owner deletes job -> 200 OK
        del_res = await ac.delete(f"/api/v1/jobs/{job1_id}", headers=recruiter_1_h)
        assert del_res.status_code == 200
        assert del_res.json()["message"] == "Job deleted successfully"
