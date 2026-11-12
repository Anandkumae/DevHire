import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.cache import get_cache_stats, invalidate_cache_pattern


@pytest.mark.anyio
async def test_redis_jobs_caching_and_invalidation():
    # Invalidate existing cache before test
    await invalidate_cache_pattern("jobs:*")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First request: should MISS cache
        res1 = await ac.get("/api/v1/jobs?limit=5")
        assert res1.status_code == 200
        assert res1.headers.get("X-Cache") == "MISS"
        data1 = res1.json()

        # Second request: identical parameters should HIT cache
        res2 = await ac.get("/api/v1/jobs?limit=5")
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") == "HIT"
        data2 = res2.json()

        assert data1 == data2

        # Check cache stats
        stats = await get_cache_stats()
        assert stats["status"] == "connected"
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["hit_ratio_percent"] > 0

        # Invalidate pattern manually or via job mutation
        await invalidate_cache_pattern("jobs:*")

        # Third request: should MISS again because cache was invalidated
        res3 = await ac.get("/api/v1/jobs?limit=5")
        assert res3.status_code == 200
        assert res3.headers.get("X-Cache") == "MISS"

