import sys
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def get_client_identifier(request: Request) -> str:
    """Identify client by Authorization token if present, otherwise by IP address."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1][:32]
    return get_remote_address(request)


# Disable limiter by default during pytest test suites to avoid 429 collisions across tests
is_testing = "pytest" in sys.modules

# Initialize limiter with Redis storage fallback to memory
try:
    limiter = Limiter(
        key_func=get_client_identifier,
        default_limits=["120/minute"],
        storage_uri=settings.REDIS_URL,
        enabled=not is_testing,
    )
except Exception:
    limiter = Limiter(
        key_func=get_client_identifier,
        default_limits=["120/minute"],
        enabled=not is_testing,
    )


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Standardized 429 Too Many Requests response handler."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )

