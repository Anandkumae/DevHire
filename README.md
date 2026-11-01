# DevHire — Enterprise AI Applicant Tracking System (ATS)

[![CI/CD Pipeline](https://github.com/Anandkumae/DevHire/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Anandkumae/DevHire/actions/workflows/ci-cd.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black.svg?logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.6-37814A.svg?logo=celery)](https://docs.celeryq.dev)

**DevHire** is a high-throughput, enterprise-grade recruitment and Applicant Tracking System (ATS). It pairs candidates with jobs using an **AI Resume Matching Engine** (TF-IDF semantic relevance and technical skill extraction), coordinates distributed background tasks with **Celery & Redis**, provides **real-time WebSocket notifications**, and powers an intuitive **Next.js 14** web application for both candidates and recruiters.

---

## Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Next.js 14 Frontend     │
                          │ (Candidate & Recruiter)   │
                          └─────────────┬─────────────┘
                                        │ REST / WebSockets
                                        ▼
                          ┌───────────────────────────┐
                          │      FastAPI Backend      │
                          │   (Async Python 3.12)     │
                          └──────┬────────────┬───────┘
                                 │            │
            ┌────────────────────┼────────────┼────────────────────┐
            ▼                    ▼            ▼                    ▼
   ┌─────────────────┐  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐
   │  PostgreSQL 16  │  │   Redis 7   │  │ Celery Queue │  │  AWS S3 /     │
   │ (ACID & Migr.)  │  │ (PubSub &   │  │ (AI Matching,│  │ Local Object  │
   │                 │  │  Caching)   │  │  Emails)     │  │ Storage       │
   └─────────────────┘  └─────────────┘  └──────────────┘  └───────────────┘
```

---

## Key Modules & Features

### 1. Authentication & Role-Based Access Control (RBAC)
- Argon2id password hashing and JWT authentication with automatic token refresh rotation.
- Strict multi-tenant roles: `candidate`, `recruiter`, and `admin`.

### 2. Company & Job Requisition Management
- Recruiter company registration with company-scoped job authorization.
- Advanced multi-filter job search (overlapping salary range, location, employment type, experience level, full-text keywords).

### 3. Application Lifecycle & Audit State Machine
- Strict status transitions: `applied` $\to$ `under_review` $\to$ `shortlisted` $\to$ `interview` $\to$ `selected` / `rejected`.
- Complete immutable audit trail (`application_status_history`) tracking state changes, timestamps, and reviewer notes.

### 4. Resume Storage & AWS S3
- PDF resume upload validation with magic byte verification and 5MB size limit.
- Presigned S3 GET/PUT URLs with seamless fallback to local disk storage for local testing and offline setups.

### 5. AI Resume Matching Engine
- Automated PDF text extraction via `pypdf`.
- Technical skill parser with support for multi-character tokens (`C++`, `.NET`, `Node.js`, `FastAPI`).
- Scikit-Learn TF-IDF vectorization with sublinear scaling and cosine similarity.
- Experience level heuristics evaluating seniority signals and years of experience.
- Recruiter **Ranked Candidate Dashboard** providing transparent explainability (matching skills, missing skills, strengths, and gap analysis).

### 6. Distributed Background Task Processing
- Celery worker cluster with Redis broker.
- Asynchronous email notifications (application confirmation, status updates, interview invitations).
- Exponential backoff autoretry mechanisms.

### 7. Real-Time WebSocket Notification System
- WebSocket connection endpoint at `/api/v1/notifications/ws/{user_id}`.
- Distributed fan-out using Redis Pub/Sub.
- Live badge counters and instant candidate alerts.

### 8. Full-Stack Next.js 14 Integration
- **Candidate Portal**: Job discovery, rich application modal, application journey pipeline tracking, and explainable AI match report.
- **Recruiter Dashboard**: Requisition posting, applicant management, one-click candidate ranking by AI match score, and interview scheduler.

---

## Quick Start (Docker Compose)

The easiest way to run the entire DevHire platform is with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/Anandkumae/DevHire.git
cd DevHire

# Start all services (PostgreSQL, Redis, FastAPI Backend, Celery Worker)
docker-compose up --build
```

Access the services:
- **FastAPI API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Next.js Frontend**: [http://localhost:3000](http://localhost:3000)

---

## Local Development (Native)

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- PostgreSQL 16
- Redis 7

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run FastAPI dev server
uvicorn app.main:app --reload --port 8000

# In a separate terminal, run Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

---

## Automated Testing & Quality Assurance

DevHire includes automated tests covering unit models, API endpoints, background tasks, and AI matching:

```bash
cd backend

# Run the complete test suite
pytest app/tests -v
```

### Load Testing with Locust
```bash
cd backend

# Run headless load simulation
locust -f load_tests/locustfile.py --headless -u 20 -r 5 -t 30s --host http://localhost:8000
```

---

## Repository Structure

```
DevHire/
├── .github/workflows/          # GitHub Actions CI/CD Pipeline
├── backend/
│   ├── alembic/                # Database migrations
│   ├── app/
│   │   ├── core/               # Configuration, S3 storage, AI engine, WebSockets
│   │   ├── database/           # Async SQLAlchemy session and base
│   │   ├── models/             # Relational data models
│   │   ├── modules/            # Domain modules (auth, jobs, applications, matching, etc.)
│   │   ├── tests/              # 30+ Pytest unit and integration tests
│   │   └── workers/            # Celery tasks (emails, AI scoring, resume processing)
│   ├── load_tests/             # Locust user behavior simulations
│   ├── Dockerfile              # Multi-stage production container image
│   └── requirements.txt        # Python package specifications
├── frontend/
│   ├── app/                    # Next.js 14 App Router pages
│   ├── components/             # Reusable UI components & Navbar
│   ├── hooks/                  # Auth and WebSocket hooks
│   ├── services/               # Typed API client
│   └── types/                  # TypeScript interfaces
├── docker-compose.yml          # Local container orchestration
└── docker-compose.prod.yml     # Production overlay
```

---

## License
MIT License. Built for modern talent acquisition and recruitment engineering.
