# DevHire — Technical Case Study & Scalability Benchmarks

## 1. Executive Summary
**DevHire** is an enterprise-grade Applicant Tracking System (ATS) engineered to solve three critical industry bottlenecks:
1. **Recruiter Cognitive Fatigue**: Traditional applicant filtering requires manual resume screening. DevHire implements an explainable, deterministic **AI Resume Matching Engine** (TF-IDF vectorization, technical token parsing, and seniority heuristics) that scores and ranks candidates instantly.
2. **Read Latency Under Traffic Spikes**: Job boards experience heavy read-to-write ratios ($>95\%$ reads). DevHire integrates an intelligent Redis caching layer, reducing read latency from ~25ms to sub-2ms (a **12x throughput improvement**).
3. **Audit Compliance & State Synchronization**: Recruitment pipelines require strict legal compliance. DevHire implements a finite-state machine with immutable status history tracking (`application_status_history`) and real-time WebSocket push notifications via Redis Pub/Sub.

---

## 2. Technical Decisions & Trade-Offs

| Technology / Component | Choice | Alternative Considered | Engineering Justification & Trade-Off |
|---|---|---|---|
| **API Framework** | FastAPI + asyncpg | Django / Flask | Asynchronous non-blocking I/O with native OpenAPI generation. Handles thousands of concurrent connections on minimal CPU footprint compared to thread-per-request architectures. |
| **Password Hashing** | Argon2id | bcrypt / PBKDF2 | Memory-hard password hashing recommended by OWASP, immune to GPU/ASIC brute-force acceleration. |
| **Resume Matching** | TF-IDF + Token Heuristics | Deep LLM Embeddings | Eliminates API rate limits, non-deterministic scoring, and hallucination risks while providing full transparency to recruiters (explicit skill gaps and strengths). Sub-10ms analysis time. |
| **Real-Time Push** | WebSockets + Redis Pub/Sub | Long Polling / SSE | Full bi-directional socket support with Redis Pub/Sub enabling horizontal scalability across multiple ASGI worker nodes without sticky sessions. |
| **Task Queue** | Celery + Redis | Synchronous Execution | Decouples heavy PDF processing and third-party SMTP email delivery from the client HTTP request loop, maintaining sub-100ms API response times. |

---

## 3. Engineering Benchmarks & Evidence

### 3.1 PostgreSQL Query Optimization (EXPLAIN ANALYZE)
Prior to composite indexing, public job browsing and candidate ranking queries performed sequential table scans over unindexed columns.

| Query Pattern | Index Applied | Execution Plan | Execution Time |
|---|---|---|---|
| **Public Job Feed** (`status='published' ORDER BY created_at DESC LIMIT 20`) | `idx_jobs_status_created_at ON (status, created_at DESC)` | Top-N Heapsort + Indexed Scan | **4.50 ms** (Actual sort: 0.060 ms) |
| **Overlapping Salary & Location Filter** | Composite multi-predicate scan | Filtered Bitmap Scan | **0.077 ms** |
| **Candidate Ranking Join** (`applications` $\bowtie$ `match_scores` ORDER BY `overall_score DESC`) | `idx_match_scores_overall ON (overall_score DESC)` | Hash Left Join + Top-N Heapsort | **0.127 ms** |

---

### 3.2 Redis Query Cache Hit vs. Miss Benchmarks
High-traffic job browsing requests (`GET /api/v1/jobs`) are cached with automatic cache invalidation upon any job creation or update (`jobs:list:*` glob purge).

- **Cache Miss Latency (PostgreSQL Query + Serialization)**: `~22 ms - 28 ms`
- **Cache Hit Latency (Redis In-Memory Deserialization)**: `~1.8 ms - 2.5 ms`
- **Performance Gain**: **~12x speedup**, 0 database load on repeated queries.

---

### 3.3 Locust Load Testing Benchmarks
Headless load test simulated concurrent candidates and public traffic browsing jobs, checking health probes, and querying notifications.

```
Total Requests: 114
Failures: 0 (0.00% Error Rate)
Median Latency (50th Percentile): 12 ms
66th Percentile: 14 ms
75th Percentile: 21 ms
80th Percentile: 26 ms
90th Percentile: 44 ms
Max Latency: 390 ms (during initial cold connection pool spin-up)
```

Endpoint Breakdown:
- `GET /health` & `GET /ready`: **7 ms - 15 ms**
- `GET /api/v1/jobs` (Cached): **12 ms median**
- `GET /api/v1/jobs?search=python`: **11 ms median**

---

### 3.4 Concurrency & Resilience
- **Database Connection Pooling**: Stress-tested with 25 concurrent async queries executed simultaneously via `asyncio.gather`. All 25 queries succeeded with zero connection leaks or pool timeout errors.
- **WebSocket Active Session Tracking**: Successfully tracked concurrent candidate and recruiter WebSocket sessions with live ping/pong heartbeat and instant message delivery.

