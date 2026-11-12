import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("devhire.cache")

_redis_pool: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


async def get_cache(key: str) -> Optional[Any]:
    """Retrieve and deserialize JSON value from Redis."""
    try:
        client = get_redis_client()
        val = await client.get(key)
        if val is not None:
            await client.incr("stats:cache:hits")
            return json.loads(val)
        else:
            await client.incr("stats:cache:misses")
            return None
    except Exception as e:
        logger.warning(f"Redis get_cache error for key '{key}': {e}")
        return None


async def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> bool:
    """Serialize value to JSON and store in Redis with TTL."""
    try:
        client = get_redis_client()
        serialized = json.dumps(value, default=str)
        await client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as e:
        logger.warning(f"Redis set_cache error for key '{key}': {e}")
        return False


async def delete_cache(key: str) -> bool:
    """Delete a single key from Redis."""
    try:
        client = get_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis delete_cache error for key '{key}': {e}")
        return False


async def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate all keys matching the glob pattern using SCAN for production safety."""
    try:
        client = get_redis_client()
        deleted_count = 0
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                deleted_count += await client.delete(*keys)
            if cursor == 0:
                break
        return deleted_count
    except Exception as e:
        logger.warning(f"Redis invalidate_cache_pattern error for pattern '{pattern}': {e}")
        return 0


async def get_cache_stats() -> dict[str, Any]:
    """Return aggregated cache hit/miss statistics and hit ratio."""
    try:
        client = get_redis_client()
        hits = int(await client.get("stats:cache:hits") or 0)
        misses = int(await client.get("stats:cache:misses") or 0)
        total = hits + misses
        ratio = (hits / total * 100.0) if total > 0 else 0.0
        return {
            "hits": hits,
            "misses": misses,
            "total_lookups": total,
            "hit_ratio_percent": round(ratio, 2),
            "status": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hits": 0,
            "misses": 0,
            "total_lookups": 0,
            "hit_ratio_percent": 0.0
        }

