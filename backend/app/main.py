from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import sentry_sdk

from app.core.cache import get_redis_client
from app.core.config import settings
from app.core.limiter import limiter, rate_limit_exceeded_handler
from app.core.logging_middleware import StructuredLoggingMiddleware
from app.core.metrics import get_metrics_summary, get_prometheus_formatted_metrics
from app.core.security_middleware import SecurityHeadersMiddleware
from app.database.session import get_db
from app.modules.auth.protected_router import router as users_router, protected_router
from app.modules.auth.router import router as auth_router
from app.modules.companies.router import router as companies_router
from app.modules.jobs.router import router as jobs_router
from app.modules.applications.router import router as applications_router
from app.modules.resumes.router import router as resumes_router
from app.modules.interviews.router import router as interviews_router
from app.modules.notifications.router import router as notifications_router
from app.modules.ai_matching.router import router as ai_matching_router

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
    )

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# Production Security, Telemetry & Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)

# CORS Configuration for Frontend Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(protected_router, prefix="/api/v1")
app.include_router(companies_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(ai_matching_router, prefix="/api/v1")


@app.get("/", summary="API Root")
async def home():
    return {
        "message": "Welcome to DevHire API",
        "status": "running"
    }


@app.get("/health", summary="Liveness Probe")
@app.get("/health/live", summary="Liveness Probe")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/ready", summary="Readiness Probe")
@app.get("/health/ready", summary="Readiness Probe")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    redis_ok = False
    errors = {}

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        errors["database"] = str(e)

    try:
        r = get_redis_client()
        await r.ping()
        redis_ok = True
    except Exception as e:
        errors["redis"] = str(e)

    if db_ok and redis_ok:
        return {
            "status": "ready",
            "database": "connected",
            "redis": "connected"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not ready",
                "database": "connected" if db_ok else "disconnected",
                "redis": "connected" if redis_ok else "disconnected",
                "errors": errors
            }
        )


@app.get("/metrics", summary="Prometheus Metrics")
async def prometheus_metrics():
    """Plain-text Prometheus metrics scrape endpoint."""
    content = await get_prometheus_formatted_metrics()
    return Response(content=content, media_type="text/plain")


@app.get("/metrics/summary", summary="System Observability Telemetry")
async def metrics_summary():
    """Structured JSON telemetry endpoint for CloudWatch, dashboards, and admin monitoring."""
    return await get_metrics_summary()
