from fastapi import APIRouter, Depends
from app.models import User
from app.modules.auth.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", summary="Get current user profile")
async def get_profile(user: User = Depends(get_current_user)):
    """Return profile details for the authenticated user."""
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.get("/candidate-area", summary="Candidate-only area")
async def candidate_area(user: User = Depends(require_roles("candidate"))):
    """Protected endpoint accessible only to candidates."""
    return {
        "message": f"Welcome to candidate dashboard, {user.full_name}!",
        "role": user.role,
    }


@router.get("/recruiter-area", summary="Recruiter-only area")
async def recruiter_area(user: User = Depends(require_roles("recruiter"))):
    """Protected endpoint accessible only to recruiters."""
    return {
        "message": f"Welcome to recruiter console, {user.full_name}!",
        "role": user.role,
    }


@router.get("/admin-area", summary="Admin-only area")
async def admin_area(user: User = Depends(require_roles("admin"))):
    """Protected endpoint accessible only to administrators."""
    return {
        "message": f"Welcome to system administration, {user.full_name}!",
        "role": user.role,
    }
