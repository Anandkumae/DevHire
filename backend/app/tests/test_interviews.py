from datetime import datetime, timedelta, timezone
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
async def test_interview_management_lifecycle():
    cand_1_email = f"cand_int1_{uuid.uuid4().hex[:8]}@example.com"
    cand_2_email = f"cand_int2_{uuid.uuid4().hex[:8]}@example.com"
    rec_1_email = f"rec_int1_{uuid.uuid4().hex[:8]}@example.com"
    rec_2_email = f"rec_int2_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register users
        for email in [cand_1_email, cand_2_email, rec_1_email, rec_2_email]:
            reg_res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert reg_res.status_code == 201

        # Promote recruiters
        await promote_user_role(rec_1_email, "recruiter")
        await promote_user_role(rec_2_email, "recruiter")

        async def get_token(email: str) -> str:
            res = await ac.post("/api/v1/auth/login", json={"email": email, "password": password})
            return res.json()["access_token"]

        cand1_h = {"Authorization": f"Bearer {await get_token(cand_1_email)}"}
        cand2_h = {"Authorization": f"Bearer {await get_token(cand_2_email)}"}
        rec1_h = {"Authorization": f"Bearer {await get_token(rec_1_email)}"}
        rec2_h = {"Authorization": f"Bearer {await get_token(rec_2_email)}"}

        # Recruiter 1 creates company and job
        comp_res = await ac.post("/api/v1/companies", json={
            "name": f"Hiring Dynamics {uuid.uuid4().hex[:6]}",
            "description": "Talent platform",
            "location": "Noida, India"
        }, headers=rec1_h)
        assert comp_res.status_code == 201

        job_res = await ac.post("/api/v1/jobs", json={
            "title": "Principal Distributed Systems Engineer",
            "description": "Design high-concurrency event queues and distributed caching.",
            "location": "Noida (Hybrid)",
            "employment_type": "full-time",
            "experience_level": "senior",
            "status": "published"
        }, headers=rec1_h)
        assert job_res.status_code == 201
        job_id = job_res.json()["id"]

        # Candidate 1 applies to the job
        apply_res = await ac.post("/api/v1/applications", json={
            "job_id": job_id,
            "cover_letter": "Passionate about high-throughput distributed systems."
        }, headers=cand1_h)
        assert apply_res.status_code == 201
        app_id = apply_res.json()["id"]

        # 1. Recruiter 1 schedules Interview 1 for Candidate 1 -> 201 Created
        interview_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        int1_req = {
            "application_id": app_id,
            "round_name": "Technical System Design",
            "interview_type": "video",
            "scheduled_at": interview_time,
            "duration_minutes": 60,
            "meeting_link": "https://meet.google.com/xyz-uvwx-rst",
            "notes": "Focus on horizontal scaling and message brokers."
        }
        int1_res = await ac.post("/api/v1/interviews", json=int1_req, headers=rec1_h)
        assert int1_res.status_code == 201
        int1_data = int1_res.json()
        assert int1_data["round_name"] == "Technical System Design"
        assert int1_data["status"] == "scheduled"
        interview_1_id = int1_data["id"]

        # Verify application status automatically progressed to 'interview'
        app_check_res = await ac.get(f"/api/v1/applications/{app_id}", headers=cand1_h)
        assert app_check_res.json()["status"] == "interview"

        # 2. Candidate 1 lists their scheduled interviews -> 200 OK
        cand_ints_res = await ac.get("/api/v1/interviews/my-interviews", headers=cand1_h)
        assert cand_ints_res.status_code == 200
        assert any(i["id"] == interview_1_id for i in cand_ints_res.json())

        # 3. Candidate 2 cannot access Candidate 1's interview -> 403 Forbidden
        unauth_cand_int = await ac.get(f"/api/v1/interviews/{interview_1_id}", headers=cand2_h)
        assert unauth_cand_int.status_code == 403

        # 4. Recruiter 2 (different company) cannot reschedule -> 404 Not Found
        reschedule_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        diff_resched = await ac.patch(
            f"/api/v1/interviews/{interview_1_id}/reschedule",
            json={"scheduled_at": reschedule_time},
            headers=rec2_h
        )
        assert diff_resched.status_code == 404

        # 5. Recruiter 1 successfully reschedules the interview -> 200 OK
        resched_res = await ac.patch(
            f"/api/v1/interviews/{interview_1_id}/reschedule",
            json={
                "scheduled_at": reschedule_time,
                "duration_minutes": 75,
                "meeting_link": "https://zoom.us/j/9876543210"
            },
            headers=rec1_h
        )
        assert resched_res.status_code == 200
        assert resched_res.json()["status"] == "rescheduled"
        assert resched_res.json()["duration_minutes"] == 75

        # 6. Invalid feedback rating (score 6 > 5) -> 422 Unprocessable Entity
        bad_rating_res = await ac.post(
            f"/api/v1/interviews/{interview_1_id}/feedback",
            json={
                "rating": 6,
                "overall_feedback": "Invalid rating test rubric",
                "recommendation": "hire"
            },
            headers=rec1_h
        )
        assert bad_rating_res.status_code == 422

        # 7. Recruiter 1 submits valid structured evaluation feedback -> 201 Created
        feedback_payload = {
            "rating": 5,
            "technical_skills": "Exceptional concurrency models and distributed systems architecture.",
            "soft_skills": "Very articulate and collaborative.",
            "overall_feedback": "Exceeded all bar requirements for the Principal role.",
            "recommendation": "strong_hire"
        }
        feedback_res = await ac.post(
            f"/api/v1/interviews/{interview_1_id}/feedback",
            json=feedback_payload,
            headers=rec1_h
        )
        assert feedback_res.status_code == 201
        fb_data = feedback_res.json()
        assert fb_data["rating"] == 5
        assert fb_data["recommendation"] == "strong_hire"

        # Verify interview status became 'completed'
        int1_completed_res = await ac.get(f"/api/v1/interviews/{interview_1_id}", headers=rec1_h)
        assert int1_completed_res.json()["status"] == "completed"

        # 8. Duplicate feedback submission is blocked -> 409 Conflict
        dup_feedback_res = await ac.post(
            f"/api/v1/interviews/{interview_1_id}/feedback",
            json=feedback_payload,
            headers=rec1_h
        )
        assert dup_feedback_res.status_code == 409
        assert "Feedback has already been submitted" in dup_feedback_res.json()["detail"]

        # 9. Schedule a second round interview, then cancel it
        int2_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        int2_res = await ac.post("/api/v1/interviews", json={
            "application_id": app_id,
            "round_name": "Leadership Round",
            "scheduled_at": int2_time,
            "duration_minutes": 45
        }, headers=rec1_h)
        assert int2_res.status_code == 201
        interview_2_id = int2_res.json()["id"]

        cancel_res = await ac.patch(
            f"/api/v1/interviews/{interview_2_id}/cancel?reason=Candidate+advanced+directly",
            headers=rec1_h
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

        # 10. Cannot reschedule a cancelled interview -> 400 Bad Request
        cannot_resched_res = await ac.patch(
            f"/api/v1/interviews/{interview_2_id}/reschedule",
            json={"scheduled_at": reschedule_time},
            headers=rec1_h
        )
        assert cannot_resched_res.status_code == 400
        assert "Cannot reschedule a cancelled interview" in cannot_resched_res.json()["detail"]

