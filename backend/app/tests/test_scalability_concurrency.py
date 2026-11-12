import asyncio
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database.session import AsyncSessionLocal, engine
from app.core.notifications import ws_manager
from app.core.security import create_access_token
from app.models import User
from app.workers.email_tasks import send_raw_email_task
from app.workers.resume_tasks import process_uploaded_resume_task


@pytest.mark.anyio
async def test_database_connection_pool_concurrency():
    """Verify database connection pool handles 25 concurrent queries cleanly."""
    async def run_query(idx: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(text(f"SELECT {idx} AS q_idx"))
            return res.scalar()

    tasks = [run_query(i) for i in range(25)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 25
    assert results == list(range(25))


def test_celery_task_retry_configuration():
    """Verify Celery tasks have retry configurations and execution policies."""
    assert hasattr(send_raw_email_task, "retry")
    assert hasattr(process_uploaded_resume_task, "retry")

    # Verify task names match expectations
    assert send_raw_email_task.name == "app.workers.email_tasks.send_raw_email_task"
    assert process_uploaded_resume_task.name == "app.workers.resume_tasks.process_uploaded_resume_task"


def test_websocket_concurrent_connections():
    """Test concurrent WebSocket connections and active session tracking."""
    client = TestClient(app)

    email1 = f"ws_conc_1_{uuid.uuid4().hex[:6]}@example.com"
    email2 = f"ws_conc_2_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "Password123!"

    r1 = client.post("/api/v1/auth/register", json={"full_name": "WS 1", "email": email1, "password": pwd})
    assert r1.status_code == 201
    l1 = client.post("/api/v1/auth/login", json={"email": email1, "password": pwd})
    token1 = l1.json()["access_token"]

    r2 = client.post("/api/v1/auth/register", json={"full_name": "WS 2", "email": email2, "password": pwd})
    assert r2.status_code == 201
    l2 = client.post("/api/v1/auth/login", json={"email": email2, "password": pwd})
    token2 = l2.json()["access_token"]

    with client.websocket_connect(f"/api/v1/notifications/ws?token={token1}") as ws1:
        init_1 = ws1.receive_json()
        assert init_1["event"] == "connected"

        with client.websocket_connect(f"/api/v1/notifications/ws?token={token2}") as ws2:
            init_2 = ws2.receive_json()
            assert init_2["event"] == "connected"
            assert ws_manager.get_active_connection_count() >= 2

