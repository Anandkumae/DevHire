import io
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
async def test_resume_management_lifecycle():
    cand_1_email = f"cand_res1_{uuid.uuid4().hex[:8]}@example.com"
    cand_2_email = f"cand_res2_{uuid.uuid4().hex[:8]}@example.com"
    rec_1_email = f"rec_res1_{uuid.uuid4().hex[:8]}@example.com"
    rec_2_email = f"rec_res2_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register users
        for email in [cand_1_email, cand_2_email, rec_1_email, rec_2_email]:
            reg_res = await ac.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": email,
                "password": password
            })
            assert reg_res.status_code == 201

        # Promote recruiters
        await promote_user_role(rec_1_email, "recruiter")
        await promote_user_role(rec_2_email, "recruiter")

        async def get_token(email: str) -> str:
            res = await ac.post("/api/v1/auth/login", json={"email": email, "password": password})
            return res.json()["access_token"]

        cand1_h = {"Authorization": f"Bearer {await get_token(cand_1_email)}"}
        cand2_h = {"Authorization": f"Bearer {await get_token(cand_2_email)}"}
        rec1_h = {"Authorization": f"Bearer {await get_token(rec_1_email)}"}
        rec2_h = {"Authorization": f"Bearer {await get_token(rec_2_email)}"}

        # Recruiter 1 creates company and published job
        comp1_res = await ac.post("/api/v1/companies", json={
            "name": f"Cloud Innovations {uuid.uuid4().hex[:6]}",
            "description": "Cloud infra",
            "website": "https://cloud.io",
            "location": "Hyderabad, India"
        }, headers=rec1_h)
        assert comp1_res.status_code == 201

        job1_res = await ac.post("/api/v1/jobs", json={
            "title": "Cloud Systems Architect",
            "description": "Architect scalable AWS S3 and ECS infrastructure.",
            "location": "Hyderabad",
            "employment_type": "full-time",
            "experience_level": "senior",
            "status": "published"
        }, headers=rec1_h)
        assert job1_res.status_code == 201
        job1_id = job1_res.json()["id"]

        # 1. Validation: Reject non-PDF file extension (.docx)
        fake_docx = (b"Fake Word document contents", "my_resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        docx_res = await ac.post(
            "/api/v1/resumes/upload",
            files={"file": ("my_resume.docx", io.BytesIO(b"Fake Word doc"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=cand1_h
        )
        assert docx_res.status_code == 400
        assert "Only PDF documents (.pdf) are allowed" in docx_res.json()["detail"]

        # 2. Validation: Reject corrupted PDF (missing %PDF- magic bytes)
        fake_pdf = b"NOT_A_REAL_PDF_HEADER"
        corrupt_res = await ac.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.pdf", io.BytesIO(fake_pdf), "application/pdf")},
            headers=cand1_h
        )
        assert corrupt_res.status_code == 400
        assert "Corrupted or invalid PDF file header" in corrupt_res.json()["detail"]

        # 3. Validation: Reject oversized file (> 5MB)
        oversized_bytes = b"%PDF-1.4\n" + (b"0" * (5 * 1024 * 1024 + 100))
        oversize_res = await ac.post(
            "/api/v1/resumes/upload",
            files={"file": ("huge_resume.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
            headers=cand1_h
        )
        assert oversize_res.status_code == 400
        assert "exceeds maximum allowed size" in oversize_res.json()["detail"]

        # 4. Successful PDF upload for Candidate 1
        valid_pdf_1 = b"%PDF-1.4\n1 0 obj\n<< /Title (Candidate 1 Resume) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        upload1_res = await ac.post(
            "/api/v1/resumes/upload",
            files={"file": ("arjun_primary_resume.pdf", io.BytesIO(valid_pdf_1), "application/pdf")},
            headers=cand1_h
        )
        assert upload1_res.status_code == 201
        res1_data = upload1_res.json()
        assert res1_data["file_name"] == "arjun_primary_resume.pdf"
        assert res1_data["is_primary"] is True
        assert "download_url" in res1_data
        resume_1_id = res1_data["id"]

        # 5. S3 Presigned Upload URL generation for direct client upload
        presigned_req = {
            "file_name": "arjun_specialized_resume.pdf",
            "file_size_bytes": 2048576,
            "content_type": "application/pdf"
        }
        presigned_res = await ac.post("/api/v1/resumes/presigned-upload", json=presigned_req, headers=cand1_h)
        assert presigned_res.status_code == 201
        presigned_data = presigned_res.json()
        assert "upload_url" in presigned_data
        assert presigned_data["method"] == "PUT"
        resume_2_id = presigned_data["resume_id"]

        # 6. Candidate 1 lists their resumes -> returns both
        list_res = await ac.get("/api/v1/resumes/my-resumes", headers=cand1_h)
        assert list_res.status_code == 200
        resumes_list = list_res.json()
        assert len(resumes_list) == 2
        # Latest uploaded (resume 2) is primary
        assert any(r["id"] == resume_2_id and r["is_primary"] is True for r in resumes_list)

        # 7. Candidate 1 switches primary back to resume 1
        set_prim_res = await ac.patch(f"/api/v1/resumes/{resume_1_id}/primary", headers=cand1_h)
        assert set_prim_res.status_code == 200
        assert set_prim_res.json()["is_primary"] is True

        # Verify resume 2 is no longer primary
        res2_check = await ac.get(f"/api/v1/resumes/{resume_2_id}", headers=cand1_h)
        assert res2_check.json()["is_primary"] is False

        # 8. Candidate 2 cannot access Candidate 1's resume -> 403 Forbidden
        unauth_cand_res = await ac.get(f"/api/v1/resumes/{resume_1_id}", headers=cand2_h)
        assert unauth_cand_res.status_code == 403

        # 9. Recruiter 1 cannot access resume BEFORE candidate applies -> 403 Forbidden
        early_rec_res = await ac.get(f"/api/v1/resumes/{resume_1_id}", headers=rec1_h)
        assert early_rec_res.status_code == 403

        # 10. Candidate 1 applies to Job 1 WITHOUT providing explicit resume_url -> Auto-attaches primary resume!
        apply_res = await ac.post("/api/v1/applications", json={
            "job_id": job1_id,
            "cover_letter": "Enthusiastic engineer with AWS and S3 integration experience."
        }, headers=cand1_h)
        assert apply_res.status_code == 201
        app_data = apply_res.json()
        assert app_data["resume_url"] is not None
        assert "resume" in app_data["resume_url"]

        # 11. Now Recruiter 1 CAN access Candidate 1's resume (because candidate applied to their job) -> 200 OK
        rec_access_res = await ac.get(f"/api/v1/resumes/{resume_1_id}", headers=rec1_h)
        assert rec_access_res.status_code == 200
        assert "download_url" in rec_access_res.json()

        # 12. Recruiter 2 (different company) still CANNOT access Candidate 1's resume -> 403 Forbidden
        diff_rec_res = await ac.get(f"/api/v1/resumes/{resume_1_id}", headers=rec2_h)
        assert diff_rec_res.status_code == 403

        # 13. Candidate deletes resume 1 -> 200 OK
        del_res = await ac.delete(f"/api/v1/resumes/{resume_1_id}", headers=cand1_h)
        assert del_res.status_code == 200
        assert del_res.json()["message"] == "Resume deleted successfully"

        # Verify resume 2 was promoted to primary
        res2_promoted = await ac.get(f"/api/v1/resumes/{resume_2_id}", headers=cand1_h)
        assert res2_promoted.json()["is_primary"] is True

