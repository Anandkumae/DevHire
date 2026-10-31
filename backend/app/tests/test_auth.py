import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_auth_full_lifecycle():
    # Use unique email per test run
    unique_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register candidate
        reg_payload = {
            "full_name": "Anand Kumar",
            "email": unique_email,
            "password": password
        }
        reg_res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == unique_email
        assert reg_data["role"] == "candidate"
        assert reg_data["is_active"] is True
        assert "id" in reg_data

        # 2. Duplicate registration returns 409 Conflict
        dup_res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 409
        assert dup_res.json()["detail"] == "Email already registered"

        # 3. Login with wrong password returns 401
        bad_login_res = await ac.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "WrongPassword123"
        })
        assert bad_login_res.status_code == 401

        # 4. Successful login returns access and refresh token pair
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": password
        })
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 5. Access protected /users/me
        me_res = await ac.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == unique_email
        assert me_data["role"] == "candidate"

        # 6. Access /users/me without token fails
        no_auth_res = await ac.get("/api/v1/users/me")
        assert no_auth_res.status_code in (401, 403)

        # 7. Candidate area accessible
        candidate_res = await ac.get("/api/v1/users/candidate-area", headers=headers)
        assert candidate_res.status_code == 200
        assert candidate_res.json()["role"] == "candidate"

        # 8. Recruiter area blocked for candidate (403 Forbidden)
        recruiter_res = await ac.get("/api/v1/users/recruiter-area", headers=headers)
        assert recruiter_res.status_code == 403

        # 9. Admin area blocked for candidate (403 Forbidden)
        admin_res = await ac.get("/api/v1/users/admin-area", headers=headers)
        assert admin_res.status_code == 403

        # 10. Refresh token rotation succeeds
        refresh_res = await ac.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_res.status_code == 200
        new_token_data = refresh_res.json()
        assert "access_token" in new_token_data
        assert "refresh_token" in new_token_data
        new_refresh_token = new_token_data["refresh_token"]

        # 11. Old refresh token reuse fails (Revocation / rotation check)
        reused_refresh_res = await ac.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert reused_refresh_res.status_code == 401

        # 12. New refresh token can be used to authenticate with new access token
        new_access_token = new_token_data["access_token"]
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        new_me_res = await ac.get("/api/v1/users/me", headers=new_headers)
        assert new_me_res.status_code == 200
        assert new_me_res.json()["email"] == unique_email
