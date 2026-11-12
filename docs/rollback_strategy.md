# DevHire — Rollback Strategy & Disaster Recovery Playbook

## 1. Principles of Zero-Downtime Rollbacks
1. **Backward-Compatible Schema Changes (Expand and Contract)**:
   - Database migrations must never rename or delete columns in the same release where new code is deployed.
   - New fields are added as nullable or with defaults.
   - Code is updated to read from both or the new field.
   - Older columns are safely removed in subsequent releases.
2. **Blue/Green Deployment with Health Check Gating**:
   - The Application Load Balancer routes traffic to the Green environment only after `/health/ready` returns HTTP 200 (verifying both PostgreSQL and Redis connectivity).
   - If `/health/ready` fails, traffic remains on the Blue environment.

---

## 2. Automated Rollback Procedures

### Scenario A: Application Bug in New Code (Schema Unchanged)
Revert traffic to previous stable Docker image tag:
```bash
# Redeploy the previous Git SHA container
docker tag devhire-api:<previous-commit-sha> devhire-api:latest
docker compose restart backend worker
```

### Scenario B: Migration Reversal Required
If a newly applied Alembic migration causes issues:
```bash
cd backend
python scripts/rollback_deployment.py --steps 1 --verify-url http://127.0.0.1:8000
```
This executes `alembic downgrade -1` and verifies `/health/ready` passes before exiting.

### Scenario C: Catastrophic Database Failure / Data Corruption
To restore the database from an automated backup dump:
```bash
cd backend
python scripts/rollback_deployment.py --restore-backup backups/devhire_db_backup_<timestamp>.dump
```

---

## 3. Disaster Recovery RTO and RPO Targets
- **Recovery Point Objective (RPO)**: $\le 1$ hour (hourly PostgreSQL logical and WAL streaming backups).
- **Recovery Time Objective (RTO)**: $\le 5$ minutes (automated script recovery and container restart).

