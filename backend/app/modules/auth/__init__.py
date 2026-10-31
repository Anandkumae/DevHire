"""DevHire Authentication Module"""
from app.modules.auth.router import router as auth_router
from app.modules.auth.protected_router import router as user_router

__all__ = ["auth_router", "user_router"]
