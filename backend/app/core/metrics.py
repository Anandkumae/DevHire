import time
from typing import Any
from collections import defaultdict
from app.core.cache import get_cache_stats, get_redis_client
from app.core.notifications import ws_manager

_start_time = time.time()
_request_counts = defaultdict(int)
_status_counts = defaultdict(int)
_durations: list[float] = []
MAX_DURATION_SAMPLES = 1000


def record_request_metric(method: str, path: str, status_code: int, duration_ms: float) -> None:
    endpoint_key = f"{method}:{path}"
    _request_counts[endpoint_key] += 1
    _status_counts[status_code] += 1
    _durations.append(duration_ms)
    if len(_durations) > MAX_DURATION_SAMPLES:
        _durations.pop(0)


async def get_metrics_summary() -> dict[str, Any]:
    uptime = round(time.time() - _start_time, 2)
    total_reqs = sum(_status_counts.values())
    errors_5xx = sum(count for code, count in _status_counts.items() if code >= 500)
    errors_4xx = sum(count for code, count in _status_counts.items() if 400 <= code < 500)
    error_rate = round(((errors_5xx + errors_4xx) / total_reqs * 100.0), 2) if total_reqs > 0 else 0.0
    avg_latency = round(sum(_durations) / len(_durations), 2) if _durations else 0.0

    # Redis Cache telemetry
    cache_telemetry = await get_cache_stats()

    # Redis ping check
    redis_healthy = False
    try:
        r = get_redis_client()
        await r.ping()
        redis_healthy = True
    except Exception:
        redis_healthy = False

    return {
        "service": "DevHire ATS API",
        "uptime_seconds": uptime,
        "traffic": {
            "total_requests": total_reqs,
            "error_rate_percent": error_rate,
            "avg_latency_ms": avg_latency,
            "status_codes": dict(_status_counts)
        },
        "cache": cache_telemetry,
        "realtime": {
            "active_websockets": ws_manager.get_active_connection_count()
        },
        "dependencies": {
            "redis_connected": redis_healthy
        }
    }


async def get_prometheus_formatted_metrics() -> str:
    summary = await get_metrics_summary()
    lines = [
        "# HELP devhire_uptime_seconds Total application uptime in seconds",
        "# TYPE devhire_uptime_seconds gauge",
        f"devhire_uptime_seconds {summary['uptime_seconds']}",
        "",
        "# HELP devhire_http_requests_total Total number of HTTP requests processed",
        "# TYPE devhire_http_requests_total counter",
        f"devhire_http_requests_total {summary['traffic']['total_requests']}",
        "",
        "# HELP devhire_http_error_rate_percent HTTP 4xx/5xx error rate percentage",
        "# TYPE devhire_http_error_rate_percent gauge",
        f"devhire_http_error_rate_percent {summary['traffic']['error_rate_percent']}",
        "",
        "# HELP devhire_http_latency_ms Average HTTP response latency in milliseconds",
        "# TYPE devhire_http_latency_ms gauge",
        f"devhire_http_latency_ms {summary['traffic']['avg_latency_ms']}",
        "",
        "# HELP devhire_active_websocket_connections Current active WebSocket sessions",
        "# TYPE devhire_active_websocket_connections gauge",
        f"devhire_active_websocket_connections {summary['realtime']['active_websockets']}",
        "",
        "# HELP devhire_redis_cache_hits Total Redis cache hits",
        "# TYPE devhire_redis_cache_hits counter",
        f"devhire_redis_cache_hits {summary['cache'].get('hits', 0)}",
        "",
        "# HELP devhire_redis_cache_misses Total Redis cache misses",
        "# TYPE devhire_redis_cache_misses counter",
        f"devhire_redis_cache_misses {summary['cache'].get('misses', 0)}",
        "",
        "# HELP devhire_redis_cache_hit_ratio Redis cache hit ratio percentage",
        "# TYPE devhire_redis_cache_hit_ratio gauge",
        f"devhire_redis_cache_hit_ratio {summary['cache'].get('hit_ratio_percent', 0.0)}",
    ]
    return "\n".join(lines) + "\n"
