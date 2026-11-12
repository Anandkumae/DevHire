from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.database.session import get_db
from app.modules.auth.schemas import (
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.modules.auth.service import (
    login_user,
    refresh_user_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new candidate"
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account with role 'candidate'.
    Prevents self-assignment of recruiter or admin privileges.
    """
    user = await register_user(
        db=db,
        full_name=data.full_name,
        email=str(data.email),
        password=data.password
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT tokens"
)
@limiter.limit("15/minute")
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email and password, returning an access token and refresh token.
    """
    return await login_user(
        db=db,
        email=str(data.email),
        password=data.password
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token for new access token"
)
async def refresh_tokens(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange an existing valid refresh token for a new access token and rotated refresh token.
    """
    return await refresh_user_tokens(
        db=db,
        refresh_token_str=data.refresh_token
    )
