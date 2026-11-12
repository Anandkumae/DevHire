# DevHire — System Design Interview Preparation Guide

This guide prepares software engineers to discuss the architecture, engineering trade-offs, and scalability decisions of **DevHire** during senior/staff backend and system design interviews.

---

## 1. Core System Design Scenario: "Design an Enterprise Applicant Tracking System"

### Functional Requirements
- **Candidates**: Search and filter jobs by salary, location, and keywords; upload PDF resumes; apply to jobs; receive real-time notifications on application state changes.
- **Recruiters**: Post and manage job requisitions; rank candidates using AI resume matching; review candidate rubrics and schedule multi-round interviews.
- **System**: Maintain immutable audit logs for application status history; export Prometheus observability metrics; guarantee zero-downtime deployments.

### Non-Functional Requirements
- **High Read Throughput**: Support thousands of concurrent job seekers with sub-20ms latency.
- **Strict Data Consistency**: Prevent double-submission and invalid application state transitions.
- **Security & Compliance**: OWASP security headers, slowapi rate limiting, bleach input sanitization, and PDF magic-byte validation.

---

## 2. Key Architectural Interview Questions & Talking Points

### Q1: "How do you handle heavy read spikes on the job board?"
> **Talking Point**:
> "Job boards exhibit a 95:5 read-to-write ratio. In DevHire, we implemented a two-tier caching strategy. First, read queries (`GET /api/v1/jobs`) hit Redis with query-specific composite keys (`jobs:list:{filters}:{limit}:{offset}`). On a cache hit, the response is served in under 2ms directly from Redis without touching PostgreSQL.
> Second, to prevent cache staleness, we use an event-driven cache invalidation pattern: whenever a recruiter creates, updates, or closes a job, we issue an asynchronous glob scan purge (`jobs:list:*`), ensuring instant read-after-write consistency."

---

### Q2: "How do you scale real-time WebSocket notifications across multiple backend servers?"
> **Talking Point**:
> "If a user connects to Server A via WebSockets, but a background Celery worker or recruiter on Server B updates the candidate's status, Server B cannot write directly to Server A's local in-memory socket set.
> We resolved this using Redis Pub/Sub as an event bus. Each server subscribes to `notifications:*`. When an event occurs, Server B publishes the payload to `notifications:{user_id}` on Redis. Redis distributes the event to all active nodes; the node holding the candidate's socket pushes the frame across the wire. This decouples socket lifecycles from backend worker processes."

---

### Q3: "Why did you choose TF-IDF and token parsing over an LLM for resume matching?"
> **Talking Point**:
> "In an ATS, recruiters require **explainability, determinism, and zero latency**. A third-party LLM introduces three major liabilities:
> 1. **Latency & Cost**: An LLM call takes 1-3 seconds per applicant and incurs API billing. DevHire's Scikit-Learn TF-IDF vectorizer runs in under 10 milliseconds.
> 2. **Hallucination & Bias**: LLMs can hallucinate qualifications or introduce non-compliant hiring bias.
> 3. **Explainability**: DevHire provides exact mathematical sub-scores (skills score, semantic cosine similarity, experience heuristic) and explicit sets of matching vs. missing skills, giving recruiters clear auditability."

---

### Q4: "How do you secure resume uploads against malicious payloads?"
> **Talking Point**:
> "Never trust user-supplied Content-Type or file extensions. In DevHire, we implement defense-in-depth:
> 1. **Magic-Byte Inspection**: Inspect the file header for `%PDF` (hex `25 50 44 46`). Disguised executables or malicious scripts are rejected with HTTP 400.
> 2. **Payload Size Clamping**: Strictly enforce a 5MB threshold before buffering into memory or writing to storage.
> 3. **Presigned S3 URLs**: Storage is delegated to AWS S3 buckets configured with private ACLs and least-privilege IAM roles, preventing direct filesystem execution on the application server."

---

### Q5: "How do you manage database schema migrations without downtime?"
> **Talking Point**:
> "We follow the **Expand and Contract (Parallel Run)** migration pattern with Alembic:
> 1. **Phase 1 (Expand)**: Add new columns as nullable or with defaults. Apply composite indexes with `IF NOT EXISTS`.
> 2. **Phase 2 (Dual-Write / Read)**: Deploy application code that reads/writes the new structure while maintaining compatibility.
> 3. **Phase 3 (Contract)**: Safely deprecate old columns once all traffic is on the new release.
> Our automated rollback script (`scripts/rollback_deployment.py`) integrates with `/health/ready` to verify database and Redis connectivity before cutover."

