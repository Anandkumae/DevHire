# DevHire — Production Deployment Guide

## 1. Architecture Overview
DevHire is engineered as a cloud-native, decoupled micro-monolith:
- **Frontend**: Next.js 14 App Router, React 18, TailwindCSS (deployed via Vercel or AWS ECS/CloudFront).
- **Backend API**: FastAPI (Python 3.12), Uvicorn ASGI server with connection pooling and slowapi rate limiting.
- **Relational Storage**: PostgreSQL 16 with composite indexing and Alembic schema migrations.
- **Distributed Cache & Broker**: Redis 7 for query response caching (sub-millisecond reads), session rate limiting, and real-time Pub/Sub WebSocket broadcasting.
- **Background Worker Fleet**: Celery 5 with asynchronous email delivery and PDF parsing workers.
- **Object Storage**: AWS S3 with presigned URLs and magic-byte PDF validation.

---

## 2. Environment Configuration
DevHire strictly separates configuration across environments using Pydantic Settings:

| Variable | Development | Staging | Production |
|---|---|---|---|
| `ENVIRONMENT` | `development` | `staging` | `production` |
| `DEBUG` | `True` | `False` | `False` |
| `SECRET_KEY` | local default | 64-char random hex | AWS Secrets Manager / Vault |
| `DATABASE_URL` | `postgresql+asyncpg://...` (local) | AWS RDS Multi-AZ | AWS RDS PostgreSQL 16 Multi-AZ |
| `REDIS_URL` | `redis://localhost:6379/0` | AWS ElastiCache | AWS ElastiCache Cluster |
| `ALLOWED_ORIGINS` | `localhost:3000` | `staging.devhire.app` | `https://devhire.app` |

---

## 3. Docker Multi-Stage Deployment

### Local Docker Compose Orchestration
```bash
# Start PostgreSQL, Redis, Backend, Celery Worker, and Next.js frontend
docker compose up -d --build
```

### Production Docker Compose Run
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 4. Database Migrations Execution
Always execute database migrations before routing traffic to a newly deployed revision:
```bash
cd backend
alembic upgrade head
```

To verify database migration state:
```bash
alembic current
alembic check
```

---

## 5. Automated CI/CD Pipeline
Every pull request and merge to `main` executes `.github/workflows/ci-cd.yml`:
1. **Backend Tests**: Spawns isolated PostgreSQL 16 and Redis 7 containers, runs migrations, and executes all 40 pytest tests.
2. **Frontend Build**: Installs dependencies and runs `next build` with TypeScript verification.
3. **Docker Build**: Builds and tags versioned images with `${{ github.sha }}`.
4. **Staging / Production Deployment**: Automates deployment gates with environment protection rules.

