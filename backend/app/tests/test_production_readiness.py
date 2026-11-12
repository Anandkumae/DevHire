import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.limiter import limiter
from app.core.security_middleware import sanitize_input
from app.main import app


def test_input_sanitization():
    # 1. Script injection tags
    malicious_script = "<script>alert('Hacked')</script>Senior Backend Engineer"
    assert sanitize_input(malicious_script) == "alert('Hacked')Senior Backend Engineer"

    # 2. Img onerror payload
    img_payload = '<img src="x" onerror="fetch(\'http://evil.com\')">FastAPI Developer'
    assert sanitize_input(img_payload) == "FastAPI Developer"

    # 3. Safe normal text
    safe_text = "5+ years experience in Python, FastAPI, and PostgreSQL."
    assert sanitize_input(safe_text) == safe_text

    # 4. None handling
    assert sanitize_input(None) is None


def test_production_settings_validation():
    # Production with default insecure secret must fail
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure_dev_secret_key_change_me",
            DEBUG=False
        )

    # Production with DEBUG=True must fail
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="super_secret_production_key_random_value_12345",
            DEBUG=True
        )

    # Valid production settings pass
    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="super_secret_production_key_random_value_12345",
        DEBUG=False
    )
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.DEBUG is False


@pytest.mark.anyio
async def test_security_headers_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200

        # Verify OWASP security headers
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers


@pytest.mark.anyio
async def test_fake_resume_upload_rejection():
    limiter.reset()
    unique_email = f"security_cand_{uuid.uuid4().hex[:6]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register and login candidate
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "Password123!",
                "full_name": "Security Tester"
            }
        )
        assert reg_res.status_code == 201
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "Password123!"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to upload a text file disguised as a PDF
        fake_pdf = io.BytesIO(b"MALICIOUS_EXEC_OR_TEXT_DATA_NOT_A_PDF")
        upload_res = await ac.post(
            "/api/v1/resumes/upload",
            headers=headers,
            files={"file": ("malicious.pdf", fake_pdf, "application/pdf")}
        )
        assert upload_res.status_code == 400
        assert "invalid pdf" in upload_res.json()["detail"].lower()


@pytest.mark.anyio
async def test_rate_limiting_enforcement():
    limiter.enabled = True
    limiter.reset()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Login rate limit is 15/minute. Hammering it 18 times should trigger a 429
            statuses = []
            for _ in range(18):
                res = await ac.post(
                    "/api/v1/auth/login",
                    json={"email": "rate_limit_test@example.com", "password": "WrongPassword!"}
                )
                statuses.append(res.status_code)

            assert 429 in statuses
            # Verify 429 response body structure
            res_429 = await ac.post(
                "/api/v1/auth/login",
                json={"email": "rate_limit_test@example.com", "password": "WrongPassword!"}
            )
            if res_429.status_code == 429:
                data = res_429.json()
                assert "RateLimitExceeded" in data.get("error", "")
                assert "Retry-After" in res_429.headers
    finally:
        limiter.reset()
        limiter.enabled = False

