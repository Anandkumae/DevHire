import asyncio
import sys
import time
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database.session import engine


async def optimize_and_benchmark():
    print("=" * 70)
    print("DevHire — Database Query Optimization & EXPLAIN ANALYZE Benchmarks")
    print("=" * 70)

    async with engine.begin() as conn:
        print("\n1. Inspecting existing indexes on 'jobs' table...")
        res = await conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'jobs'"))
        for row in res.fetchall():
            print(f"   • {row[0]}: {row[1]}")

        print("\n2. Applying Production Performance Composite Indexes...")
        indexes_to_create = [
            ("idx_jobs_status_created_at", "CREATE INDEX IF NOT EXISTS idx_jobs_status_created_at ON jobs (status, created_at DESC)"),
            ("idx_jobs_company_status", "CREATE INDEX IF NOT EXISTS idx_jobs_company_status ON jobs (company_id, status)"),
            ("idx_applications_job_status", "CREATE INDEX IF NOT EXISTS idx_applications_job_status ON applications (job_id, status)"),
            ("idx_match_scores_overall", "CREATE INDEX IF NOT EXISTS idx_match_scores_overall ON application_match_scores (overall_score DESC)")
        ]
        for name, sql in indexes_to_create:
            await conn.execute(text(sql))
            print(f"   ✔ Index '{name}' verified / created.")

    async with engine.connect() as conn:
        print("\n3. Benchmarking Query 1: Public Job Feed (status='published' ORDER BY created_at DESC LIMIT 20)")
        query1 = text("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT id, title, location, salary_min, salary_max, created_at
            FROM jobs
            WHERE status = 'published'
            ORDER BY created_at DESC
            LIMIT 20;
        """)
        t0 = time.perf_counter()
        res1 = await conn.execute(query1)
        plan1 = "\n".join([row[0] for row in res1.fetchall()])
        dur1 = (time.perf_counter() - t0) * 1000
        print(f"Execution time: {dur1:.2f} ms")
        print("Plan Output:")
        print(plan1)

        print("\n4. Benchmarking Query 2: Overlapping Salary Filter & Location Search")
        query2 = text("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT id, title, location, salary_min, salary_max
            FROM jobs
            WHERE status = 'published'
              AND (location ILIKE '%Remote%' OR location ILIKE '%Bangalore%')
              AND (salary_max IS NULL OR salary_max >= 100000)
              AND (salary_min IS NULL OR salary_min <= 200000)
            ORDER BY created_at DESC
            LIMIT 20;
        """)
        t0 = time.perf_counter()
        res2 = await conn.execute(query2)
        plan2 = "\n".join([row[0] for row in res2.fetchall()])
        dur2 = (time.perf_counter() - t0) * 1000
        print(f"Execution time: {dur2:.2f} ms")
        print("Plan Output:")
        print(plan2)

        print("\n5. Benchmarking Query 3: Recruiter Candidate Ranking Join")
        query3 = text("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT a.id, a.candidate_id, m.overall_score, m.skills_score, m.semantic_score, m.experience_score
            FROM applications a
            LEFT JOIN application_match_scores m ON m.application_id = a.id
            WHERE a.status != 'rejected'
            ORDER BY m.overall_score DESC NULLS LAST
            LIMIT 20;
        """)
        t0 = time.perf_counter()
        res3 = await conn.execute(query3)
        plan3 = "\n".join([row[0] for row in res3.fetchall()])
        dur3 = (time.perf_counter() - t0) * 1000
        print(f"Execution time: {dur3:.2f} ms")
        print("Plan Output:")
        print(plan3)

    print("\n" + "=" * 70)
    print("Optimization and Benchmarks completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(optimize_and_benchmark())
