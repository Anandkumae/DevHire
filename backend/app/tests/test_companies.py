import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models import User


async def promote_user_role(email: str, role: str):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.email == email).values(role=role)
        )
        await session.commit()


@pytest.mark.anyio
async def test_company_api_lifecycle():
    candidate_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
    other_recruiter_email = f"other_recruiter_{uuid.uuid4().hex[:8]}@example.com"
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register users
        for email in [candidate_email, recruiter_email, other_recruiter_email, admin_email]:
            reg_res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert reg_res.status_code == 201

        # Promote users to their roles
        await promote_user_role(recruiter_email, "recruiter")
        await promote_user_role(other_recruiter_email, "recruiter")
        await promote_user_role(admin_email, "admin")

        # Obtain tokens
        candidate_res = await ac.post("/api/v1/auth/login", json={"email": candidate_email, "password": password})
        candidate_token = candidate_res.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

        recruiter_res = await ac.post("/api/v1/auth/login", json={"email": recruiter_email, "password": password})
        recruiter_token = recruiter_res.json()["access_token"]
        recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

        other_recruiter_res = await ac.post("/api/v1/auth/login", json={"email": other_recruiter_email, "password": password})
        other_recruiter_token = other_recruiter_res.json()["access_token"]
        other_recruiter_headers = {"Authorization": f"Bearer {other_recruiter_token}"}

        admin_res = await ac.post("/api/v1/auth/login", json={"email": admin_email, "password": password})
        admin_token = admin_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        company_payload = {
            "name": f"DevHire Technologies {uuid.uuid4().hex[:6]}",
            "description": "Building modern recruitment solutions.",
            "website": "https://devhire.io",
            "industry": "Software Development",
            "location": "Pune, India"
        }

        # 1. Candidate tries to create company -> 403 Forbidden
        candidate_create_res = await ac.post(
            "/api/v1/companies",
            json=company_payload,
            headers=candidate_headers
        )
        assert candidate_create_res.status_code == 403

        # 2. Recruiter creates company -> 201 Created
        create_res = await ac.post(
            "/api/v1/companies",
            json=company_payload,
            headers=recruiter_headers
        )
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["name"] == company_payload["name"]
        assert created_data["description"] == company_payload["description"]
        assert created_data["website"] == company_payload["website"]
        assert created_data["industry"] == company_payload["industry"]
        assert created_data["location"] == company_payload["location"]
        assert "id" in created_data
        assert "recruiter_id" in created_data
        assert "created_at" in created_data
        company_id = created_data["id"]

        # 3. Recruiter tries to create a second company -> 409 Conflict
        dup_create_res = await ac.post(
            "/api/v1/companies",
            json={
                "name": "Second Company",
                "description": "Another company attempt"
            },
            headers=recruiter_headers
        )
        assert dup_create_res.status_code == 409
        assert dup_create_res.json()["detail"] == "You already have a registered company"

        # 4. List companies -> 200 OK
        list_res = await ac.get("/api/v1/companies")
        assert list_res.status_code == 200
        companies_list = list_res.json()
        assert any(c["id"] == company_id for c in companies_list)

        # 5. Get company by id -> 200 OK
        get_res = await ac.get(f"/api/v1/companies/{company_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == company_id
        assert get_res.json()["name"] == company_payload["name"]

        # 6. Get non-existent company -> 404 Not Found
        non_existent_id = str(uuid.uuid4())
        not_found_res = await ac.get(f"/api/v1/companies/{non_existent_id}")
        assert not_found_res.status_code == 404

        # 7. Another recruiter tries to update the company -> 403 Forbidden
        unauth_update_res = await ac.patch(
            f"/api/v1/companies/{company_id}",
            json={"description": "Hacked description"},
            headers=other_recruiter_headers
        )
        assert unauth_update_res.status_code == 403

        # 8. Owner recruiter updates company -> 200 OK
        update_res = await ac.patch(
            f"/api/v1/companies/{company_id}",
            json={
                "description": "An advanced recruitment and applicant tracking platform.",
                "location": "Bengaluru, India"
            },
            headers=recruiter_headers
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["description"] == "An advanced recruitment and applicant tracking platform."
        assert updated_data["location"] == "Bengaluru, India"
        assert updated_data["name"] == company_payload["name"]  # Unmodified field preserved

        # 9. Admin updates company -> 200 OK
        admin_update_res = await ac.patch(
            f"/api/v1/companies/{company_id}",
            json={"website": "https://global.devhire.io"},
            headers=admin_headers
        )
        assert admin_update_res.status_code == 200
        assert admin_update_res.json()["website"] == "https://global.devhire.io"

