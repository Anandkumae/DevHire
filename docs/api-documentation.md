# DevHire API Documentation

The DevHire backend provides OpenAPI 3.0 documentation directly via Swagger UI and ReDoc.

## Interactive Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Core Endpoints

### System Endpoints
| Method | Path | Description | Expected Response |
|---|---|---|---|
| `GET` | `/` | API status greeting | `{"message": "Welcome to DevHire API", "status": "running"}` |
| `GET` | `/health` | Application liveness probe | `{"status": "healthy"}` |
| `GET` | `/ready` | Database readiness probe | `{"status": "ready", "database": "connected"}` |

### Roadmap Endpoints
- **Authentication**: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/refresh`
- **Users & Profiles**: `/api/v1/users/me`, `/api/v1/candidates/profile`
- **Companies & Jobs**: `/api/v1/companies`, `/api/v1/jobs`
- **Applications**: `/api/v1/applications`, `/api/v1/applications/{id}/match-score`
