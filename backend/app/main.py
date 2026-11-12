from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import sentry_sdk

from app.core.config import settings
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
async def health():
    return {
        "status": "healthy"
    }


@app.get("/ready", summary="Readiness Probe")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not ready",
                "database": "disconnected",
                "error": str(e)
            }
        )
