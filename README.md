# Database Training Platform

Hands-on PostgreSQL training through realistic production incidents.

The application lives in [`database-training-platform/`](database-training-platform/).

## Current MVP

Learners can choose from five real PostgreSQL DBA incidents:

1. **Slow Checkout Query** — diagnose and fix an indexing/query-plan problem.
2. **Blocked Payment Transaction** — find and clear a stale transaction holding a row lock.
3. **Connection Pool Exhaustion** — identify a runaway application pool and safely reduce excess sessions.
4. **Deadlocking Transfer Procedures** — reproduce a real PostgreSQL deadlock, fix inconsistent lock ordering and prove both paths can run concurrently.
5. **Stale Reporting Transaction** — identify and clear an old reporting transaction without damaging production-style data.

The platform now includes versioned/replayable attempts, immutable scenario snapshots, reusable versioned dataset/workload templates, declarative provisioning/fault injection, deterministic grading and real PostgreSQL integration tests.

## Start locally

```bash
cd database-training-platform
docker compose up --build
```

Then open `http://localhost:5173`.

For architecture, scenario authoring, reusable assets, local connection details and the roadmap, see the [project README](database-training-platform/README.md).
