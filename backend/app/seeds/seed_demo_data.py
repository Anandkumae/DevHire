import asyncio
import uuid
from decimal import Decimal
from pwdlib import PasswordHash
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models import (
    Application,
    ApplicationMatchScore,
    ApplicationStatusHistory,
    Company,
    Interview,
    InterviewFeedback,
    Job,
    Notification,
    Skill,
    User,
)

password_hasher = PasswordHash.recommended()


async def seed_data():
    print("🌱 Seeding DevHire Demo Data...")
    async with AsyncSessionLocal() as db:
        # 1. Create Users
        users_to_create = [
            ("recruiter@techcorp.com", "Sarah Jenkins", "recruiter"),
            ("candidate@gmail.com", "Anand Kumar", "candidate"),
            ("priya.sharma@gmail.com", "Priya Sharma", "candidate"),
            ("admin@devhire.com", "DevHire Administrator", "admin"),
        ]

        users = {}
        for email, full_name, role in users_to_create:
            existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not existing:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=password_hasher.hash("Password123!"),
                    role=role,
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                users[email] = user
            else:
                users[email] = existing

        # 2. Create Company
        recruiter = users["recruiter@techcorp.com"]
        comp_existing = (await db.execute(select(Company).where(Company.recruiter_id == recruiter.id))).scalar_one_or_none()
        if not comp_existing:
            company = Company(
                name="TechCorp Cloud Innovations",
                description="Pioneering enterprise AI and distributed cloud platforms.",
                website="https://techcorp.example.com",
                industry="Software & AI",
                location="Bengaluru, India",
                recruiter_id=recruiter.id,
            )
            db.add(company)
            await db.flush()
        else:
            company = comp_existing

        # 3. Create Skills
        skills_dict = {}
        skill_names = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Redis", "Celery", "React", "Next.js", "TypeScript"]
        for s_name in skill_names:
            s_exist = (await db.execute(select(Skill).where(Skill.name == s_name))).scalar_one_or_none()
            if not s_exist:
                sk = Skill(name=s_name)
                db.add(sk)
                await db.flush()
                skills_dict[s_name] = sk
            else:
                skills_dict[s_name] = s_exist

        # 4. Create Jobs
        job_1_existing = (await db.execute(select(Job).where(Job.title == "Senior Backend AI Engineer"))).scalar_one_or_none()
        if not job_1_existing:
            job_1 = Job(
                company_id=company.id,
                title="Senior Backend AI Engineer",
                description="We are seeking an experienced Backend Engineer to architect scalable asynchronous microservices using FastAPI, PostgreSQL, Redis, and Celery. Experience with Docker and NLP pipelines is highly desirable.",
                location="Bengaluru (Hybrid)",
                employment_type="full_time",
                experience_level="senior",
                salary_min=Decimal("1800000.00"),
                salary_max=Decimal("2800000.00"),
                status="published",
                skills=[skills_dict["Python"], skills_dict["FastAPI"], skills_dict["PostgreSQL"], skills_dict["Docker"], skills_dict["Redis"]],
            )
            db.add(job_1)
            await db.flush()
        else:
            job_1 = job_1_existing

        job_2_existing = (await db.execute(select(Job).where(Job.title == "Full Stack Platform Lead"))).scalar_one_or_none()
        if not job_2_existing:
            job_2 = Job(
                company_id=company.id,
                title="Full Stack Platform Lead",
                description="Lead engineering initiatives across modern Next.js 14 frontends and high-performance Python backends. Responsible for distributed real-time WebSocket systems.",
                location="Remote",
                employment_type="full_time",
                experience_level="lead",
                salary_min=Decimal("2500000.00"),
                salary_max=Decimal("3600000.00"),
                status="published",
                skills=[skills_dict["Next.js"], skills_dict["TypeScript"], skills_dict["Python"], skills_dict["AWS"]],
            )
            db.add(job_2)
            await db.flush()
        else:
            job_2 = job_2_existing

        # 5. Create Applications & AI Match Scores
        cand_1 = users["candidate@gmail.com"]
        app_1_exist = (await db.execute(select(Application).where(Application.candidate_id == cand_1.id, Application.job_id == job_1.id))).scalar_one_or_none()
        if not app_1_exist:
            app_1 = Application(
                candidate_id=cand_1.id,
                job_id=job_1.id,
                cover_letter="I have 6+ years of senior backend engineering experience building high-throughput microservices using FastAPI, PostgreSQL, Redis, and Celery.",
                status="shortlisted",
            )
            db.add(app_1)
            await db.flush()

            # Status history
            db.add(ApplicationStatusHistory(application_id=app_1.id, from_status=None, to_status="applied", changed_by_user_id=cand_1.id, notes="Submitted application"))
            db.add(ApplicationStatusHistory(application_id=app_1.id, from_status="applied", to_status="under_review", changed_by_user_id=recruiter.id, notes="Profile under recruiter review"))
            db.add(ApplicationStatusHistory(application_id=app_1.id, from_status="under_review", to_status="shortlisted", changed_by_user_id=recruiter.id, notes="High AI match score; shortlisted"))

            # Match Score
            db.add(
                ApplicationMatchScore(
                    application_id=app_1.id,
                    overall_score=89.5,
                    skills_score=100.0,
                    semantic_score=75.0,
                    experience_score=100.0,
                    matching_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                    missing_skills=[],
                    strengths=["Matched 5 of 5 required skills: Python, FastAPI, PostgreSQL, Docker, Redis.", "Demonstrates 6+ years of relevant senior backend engineering experience."],
                    gap_analysis=["None identified for current requisition scope."],
                    summary="Strong Match (89.5%) — Candidate demonstrates exceptional alignment with technical stack and experience expectations. Highly recommended for interview.",
                )
            )

            # Notifications
            db.add(
                Notification(
                    user_id=cand_1.id,
                    type="status_updated",
                    title="Application Shortlisted!",
                    message="Congratulations! Your application for 'Senior Backend AI Engineer' has been shortlisted.",
                    data={"application_id": str(app_1.id)},
                )
            )
            db.add(
                Notification(
                    user_id=recruiter.id,
                    type="application_received",
                    title="New Ranked Application",
                    message="Anand Kumar scored 89.5% (Strong Match) for 'Senior Backend AI Engineer'.",
                    data={"application_id": str(app_1.id)},
                )
            )

        await db.commit()
        print("✅ Demo Data Seeded Successfully!")
        print("\n🔑 Demo Credentials:")
        print("  - Recruiter: recruiter@techcorp.com / Password123!")
        print("  - Candidate: candidate@gmail.com / Password123!")
        print("  - Candidate 2: priya.sharma@gmail.com / Password123!")
        print("  - Admin: admin@devhire.com / Password123!")


if __name__ == "__main__":
    asyncio.run(seed_data())
