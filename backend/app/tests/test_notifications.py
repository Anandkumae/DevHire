import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
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
async def test_notifications_full_lifecycle():
    candidate_email = f"cand_notif_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_email = f"rec_notif_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register users
        for email in [candidate_email, recruiter_email]:
            reg_res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert reg_res.status_code == 201

        await promote_user_role(recruiter_email, "recruiter")

        # Login
        cand_login = await ac.post("/api/v1/auth/login", json={"email": candidate_email, "password": password})
        cand_token = cand_login.json()["access_token"]
        cand_h = {"Authorization": f"Bearer {cand_token}"}

        rec_login = await ac.post("/api/v1/auth/login", json={"email": recruiter_email, "password": password})
        rec_token = rec_login.json()["access_token"]
        rec_h = {"Authorization": f"Bearer {rec_token}"}

        # 1. Recruiter creates company & published job
        comp_res = await ac.post("/api/v1/companies", json={
            "name": f"Event Stream Labs {uuid.uuid4().hex[:6]}",
            "description": "Real-time stream processing",
            "location": "Bengaluru, India"
        }, headers=rec_h)
        assert comp_res.status_code == 201

        job_res = await ac.post("/api/v1/jobs", json={
            "title": "Realtime Systems Engineer",
            "description": "Design WebSocket and Redis Pub/Sub infrastructure.",
            "location": "Bengaluru",
            "employment_type": "full-time",
            "experience_level": "senior",
            "status": "published"
        }, headers=rec_h)
        assert job_res.status_code == 201
        job_id = job_res.json()["id"]

        # 2. Candidate applies for the job -> Triggers recruiter notification
        apply_res = await ac.post("/api/v1/applications", json={
            "job_id": job_id,
            "cover_letter": "I specialize in event-driven systems."
        }, headers=cand_h)
        assert apply_res.status_code == 201
        app_id = apply_res.json()["id"]

        # 3. Recruiter checks their notifications -> Sees application received notification
        rec_notifs_res = await ac.get("/api/v1/notifications", headers=rec_h)
        assert rec_notifs_res.status_code == 200
        rec_notifs = rec_notifs_res.json()
        assert rec_notifs["total"] >= 1
        assert any(n["type"] == "application_received" for n in rec_notifs["items"])

        # 4. Recruiter updates application status -> Triggers candidate notification
        status_res = await ac.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "under_review", "notes": "Impressive background"},
            headers=rec_h
        )
        assert status_res.status_code == 200

        # 5. Candidate checks notifications -> Sees status update notification
        cand_notifs_res = await ac.get("/api/v1/notifications", headers=cand_h)
        assert cand_notifs_res.status_code == 200
        cand_notifs = cand_notifs_res.json()
        assert cand_notifs["unread_count"] >= 1
        update_notif = next(n for n in cand_notifs["items"] if n["type"] == "status_updated")
        notif_id = update_notif["id"]

        # 6. Candidate marks single notification as read
        read_res = await ac.patch(f"/api/v1/notifications/{notif_id}/read", headers=cand_h)
        assert read_res.status_code == 200
        assert read_res.json()["is_read"] is True

        # 7. Candidate marks all notifications as read
        read_all_res = await ac.patch("/api/v1/notifications/read-all", headers=cand_h)
        assert read_all_res.status_code == 200

        after_read_res = await ac.get("/api/v1/notifications", headers=cand_h)
        assert after_read_res.json()["unread_count"] == 0


def test_websocket_realtime_connection():
    """Verify WebSocket authentication, connection handshake, and ping-pong."""
    client = TestClient(app)

    # 1. Reject invalid token with policy violation
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/notifications/ws?token=invalid_jwt_token") as ws:
            pass

    # 2. Register candidate and obtain valid token
    unique_email = f"ws_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"
    reg = client.post("/api/v1/auth/register", json={
        "full_name": "WS Test User",
        "email": unique_email,
        "password": password
    })
    assert reg.status_code == 201

    login = client.post("/api/v1/auth/login", json={"email": unique_email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    # 3. Connect with valid token
    with client.websocket_connect(f"/api/v1/notifications/ws?token={token}") as ws:
        # Verify initial handshake message
        init_msg = ws.receive_json()
        assert init_msg["event"] == "connected"
        assert "DevHire" in init_msg["message"]

        # Verify ping/pong heartbeat
        ws.send_text("ping")
        pong = ws.receive_text()
        assert pong == "pong"

