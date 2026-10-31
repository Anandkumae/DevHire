from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.database.session import get_db

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

@app.get("/")
async def home():
    return {
        "message": "Welcome to DevHire API",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }

@app.get("/ready")
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
