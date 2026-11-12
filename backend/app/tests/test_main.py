import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_home_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to DevHire API",
        "status": "running"
    }

@pytest.mark.anyio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }

@pytest.mark.anyio
async def test_cors_preflight_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Preflight OPTIONS for /api/v1/jobs
        res_jobs = await ac.options(
            "/api/v1/jobs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert res_jobs.status_code == 200
        assert res_jobs.headers["access-control-allow-origin"] == "http://localhost:3000"

        # Preflight OPTIONS for /api/v1/protected/me and /api/v1/users/me
        res_me = await ac.options(
            "/api/v1/protected/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert res_me.status_code == 200
        assert res_me.headers["access-control-allow-origin"] == "http://localhost:3000"
