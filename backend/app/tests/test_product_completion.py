import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_admin_moderation_workflows():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
        cand_email = f"cand_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "Password123!"

        # Register users
        await ac.post("/api/v1/auth/register", json={"email": admin_email, "password": pwd, "full_name": "Admin Tester"})
        await ac.post("/api/v1/auth/register", json={"email": cand_email, "password": pwd, "full_name": "Candidate Tester"})

        # Promote admin_email in database or via login role
        from app.database.session import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == admin_email))
            user = res.scalar_one()
            user.role = "admin"
            await db.commit()

        # Login as candidate
        c_login = await ac.post("/api/v1/auth/login", json={"email": cand_email, "password": pwd})
        c_token = c_login.json()["access_token"]
        c_headers = {"Authorization": f"Bearer {c_token}"}

        # Candidate attempting admin endpoint receives 403
        c_res = await ac.get("/api/v1/admin/stats", headers=c_headers)
        assert c_res.status_code == 403

        # Login as admin
        a_login = await ac.post("/api/v1/auth/login", json={"email": admin_email, "password": pwd})
        a_token = a_login.json()["access_token"]
        a_headers = {"Authorization": f"Bearer {a_token}"}

        # Admin gets platform stats
        stats_res = await ac.get("/api/v1/admin/stats", headers=a_headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_users"] >= 2

        # Admin lists users
        users_res = await ac.get("/api/v1/admin/users?limit=10", headers=a_headers)
        assert users_res.status_code == 200
        users_list = users_res.json()
        assert len(users_list) >= 2

        # Admin suspends candidate account
        target_cand = [u for u in users_list if u["email"] == cand_email][0]
        mod_res = await ac.patch(
            f"/api/v1/admin/users/{target_cand['id']}/status",
            headers=a_headers,
            json={"is_active": False}
        )
        assert mod_res.status_code == 200
        assert mod_res.json()["is_active"] is False


@pytest.mark.anyio
async def test_end_to_end_candidate_recruiter_journey():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        rec_email = f"rec_e2e_{uuid.uuid4().hex[:6]}@example.com"
        cand_email = f"cand_e2e_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "Password123!"

        # 1. Register recruiter and candidate
        await ac.post("/api/v1/auth/register", json={"email": rec_email, "password": pwd, "full_name": "E2E Recruiter"})
        await ac.post("/api/v1/auth/register", json={"email": cand_email, "password": pwd, "full_name": "E2E Candidate"})

        from app.database.session import AsyncSessionLocal
        from app.models import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == rec_email))
            user = res.scalar_one()
            user.role = "recruiter"
            await db.commit()

        # 2. Login recruiter
        rec_login = await ac.post("/api/v1/auth/login", json={"email": rec_email, "password": pwd})
        rec_token = rec_login.json()["access_token"]
        rec_headers = {"Authorization": f"Bearer {rec_token}"}

        # 3. Recruiter creates company
        comp_res = await ac.post(
            "/api/v1/companies",
            headers=rec_headers,
            json={
                "name": f"E2E Cloud Corp {uuid.uuid4().hex[:4]}",
                "description": "Leading cloud recruitment solutions",
                "website": "https://e2ecloud.example.com",
                "location": "Bengaluru"
            }
        )
        assert comp_res.status_code == 201

        # 4. Recruiter creates and publishes job
        job_res = await ac.post(
            "/api/v1/jobs",
            headers=rec_headers,
            json={
                "title": "Principal Python Backend Architect",
                "description": "Seeking expert in Python, FastAPI, PostgreSQL, Redis, and Distributed Systems.",
                "location": "Remote",
                "employment_type": "full_time",
                "experience_level": "lead",
                "salary_min": 2500000,
                "salary_max": 4000000,
                "status": "published",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"]
            }
        )
        assert job_res.status_code == 201
        job_id = job_res.json()["id"]

        # 5. Candidate logs in and applies for job
        cand_login = await ac.post("/api/v1/auth/login", json={"email": cand_email, "password": pwd})
        cand_token = cand_login.json()["access_token"]
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        app_res = await ac.post(
            "/api/v1/applications",
            headers=cand_headers,
            json={
                "job_id": job_id,
                "cover_letter": "I have 8+ years building enterprise high-throughput FastAPI systems with Redis and PostgreSQL."
            }
        )
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        # 6. Recruiter ranks applicants for job
        match_res = await ac.get(f"/api/v1/jobs/{job_id}/ranked-candidates", headers=rec_headers)
        assert match_res.status_code == 200
        ranked = match_res.json()
        assert len(ranked) >= 1

        # 7. Recruiter moves application through valid state machine transitions:
        # applied -> under_review -> shortlisted
        review_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            headers=rec_headers,
            json={"status": "under_review", "note": "Reviewing candidate profile and AI score."}
        )
        assert review_res.status_code == 200
        assert review_res.json()["status"] == "under_review"

        shortlist_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            headers=rec_headers,
            json={"status": "shortlisted", "note": "Candidate shortlisted for technical round."}
        )
        assert shortlist_res.status_code == 200
        assert shortlist_res.json()["status"] == "shortlisted"
        assert len(shortlist_res.json()["status_history"]) == 3

