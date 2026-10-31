import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from pwdlib import PasswordHash
from app.core.config import settings

# Initialize Argon2 password hasher
password_hash = PasswordHash.recommended()
ALGORITHM = settings.ALGORITHM


def hash_password(password: str) -> str:
    """Hash a plain text password using Argon2 via pwdlib."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2 hash."""
    return password_hash.verify(plain_password, hashed_password)


def hash_refresh_token(token: str) -> str:
    """Generate a SHA-256 hash of a refresh token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    """Create a signed JWT token with expiration and unique jti."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4())
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: str, role: Optional[str] = None) -> str:
    """Create a short-lived access token."""
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "type": "access"
    }
    if role:
        payload["role"] = role
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(payload, expires_delta)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh"
    }
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(payload, expires_delta)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
