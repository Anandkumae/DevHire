import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_request_id_and_tracing_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Custom X-Request-ID propagation
        custom_trace_id = "trace-uuid-1234-5678-observability"
        res = await ac.get("/health", headers={"X-Request-ID": custom_trace_id})
        assert res.status_code == 200
        assert res.headers.get("X-Request-ID") == custom_trace_id
        assert "X-Process-Time" in res.headers

        # 2. Automatic X-Request-ID generation if omitted
        res_auto = await ac.get("/health")
        assert res_auto.status_code == 200
        assert "X-Request-ID" in res_auto.headers
        assert len(res_auto.headers["X-Request-ID"]) > 10
        assert "X-Process-Time" in res_auto.headers


@pytest.mark.anyio
async def test_health_probes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Liveness
        res_live = await ac.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "healthy"

        # Readiness
        res_ready = await ac.get("/health/ready")
        assert res_ready.status_code == 200
        data = res_ready.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["redis"] == "connected"


@pytest.mark.anyio
async def test_prometheus_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/metrics")
        assert res.status_code == 200
        assert "text/plain" in res.headers.get("content-type", "")
        content = res.text
        assert "devhire_uptime_seconds" in content
        assert "devhire_http_requests_total" in content
        assert "devhire_active_websocket_connections" in content
        assert "devhire_redis_cache_hits" in content


@pytest.mark.anyio
async def test_metrics_json_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/metrics/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "DevHire ATS API"
        assert "traffic" in data
        assert "cache" in data
        assert "realtime" in data
        assert data["dependencies"]["redis_connected"] is True

