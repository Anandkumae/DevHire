# DevHire — AI-Powered Recruitment Platform

DevHire is a modern end-to-end recruitment platform built with a high-performance asynchronous backend and responsive modern web frontend.

---

## 🏗️ Architecture & Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | FastAPI (Python 3.12+), Uvicorn |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2 (Async), asyncpg, Alembic |
| **Cache & Task Queue** | Redis 7, Celery |
| **Containerization** | Docker, Docker Compose |
| **Automated Testing** | Pytest, HTTPX, AnyIO |
| **Frontend (Roadmap)** | Next.js 14+, TypeScript, Tailwind CSS |
| **AI Integration (Roadmap)** | Resume parsing & semantic job-candidate matching |

---

## 📁 Project Directory Structure

```text
DevHire/
├── .gitignore
├── README.md
└── backend/
    ├── .env
    ├── .env.example
    ├── docker-compose.yml
    ├── requirements.txt
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    └── app/
        ├── __init__.py
        ├── main.py
        ├── core/
        │   ├── __init__.py
        │   └── config.py
        ├── database/
        │   ├── __init__.py
        │   ├── base.py
        │   └── session.py
        ├── models/
        │   └── __init__.py
        ├── schemas/
        │   └── __init__.py
        ├── modules/
        │   └── __init__.py
        ├── workers/
        │   └── __init__.py
        └── tests/
            ├── __init__.py
            └── test_main.py
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.12+**
- **Docker Desktop** (for PostgreSQL and Redis containers)
- **Git**

### 2. Environment Setup
The backend virtual environment and dependencies are already configured in `backend/.venv`.

To activate in PowerShell:
```powershell
cd d:\DevHire\backend
.\.venv\Scripts\Activate.ps1
```

If script execution is restricted on your system:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Start Database and Cache (Docker)
Ensure Docker Desktop is running, then run:
```powershell
docker compose up -d
```
Verify containers:
```powershell
docker ps
```

### 4. Run the FastAPI Development Server
```powershell
uvicorn app.main:app --reload
```

Server will be accessible at:
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Readiness**: [http://127.0.0.1:8000/ready](http://127.0.0.1:8000/ready)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 5. Running Automated Tests
```powershell
pytest app/tests -v
```

---

## 🛣️ Development Roadmap

- [x] **Phase 1: Environment Setup & Project Foundation**
- [x] **Phase 2: Docker Compose Configuration (PostgreSQL 16 & Redis 7)**
- [x] **Phase 3: Asynchronous FastAPI Connection & Health Endpoints**
- [ ] **Phase 4: Database Models & Authentication (JWT, Refresh Tokens, RBAC)**
- [ ] **Phase 5: Core Application APIs (Users, Companies, Jobs, Applications)**
- [ ] **Phase 6: Advanced Backend (Celery Workers, Redis Caching, WebSockets)**
- [ ] **Phase 7: Frontend Application (Next.js, TypeScript, Tailwind CSS)**
- [ ] **Phase 8: AI Integration (Resume Parsing & Candidate Matching)**
- [ ] **Phase 9: Testing, CI/CD, and AWS Deployment**
