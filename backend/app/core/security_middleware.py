from typing import Optional
import bleach
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce production security headers on all responses per OWASP recommendations."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking defense
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS filter activation
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HTTP Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (Allows necessary WebSockets, API calls, and inline styling)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss: http: https:;"
        )

        return response


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """
    Sanitize text input by stripping all HTML and javascript tags.
    Prevents Stored Cross-Site Scripting (XSS).
    """
    if text is None:
        return None
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned.strip()

