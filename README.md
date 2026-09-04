# Database Training Platform

Hands-on PostgreSQL training through realistic production incidents.

The current application lives in [`database-training-platform/`](database-training-platform/).

## Current MVP

Learners can choose from three real PostgreSQL DBA incidents:

1. **Slow Checkout Query** — diagnose and fix an indexing/query-plan problem.
2. **Blocked Payment Transaction** — find and clear a stale transaction holding a row lock.
3. **Connection Pool Exhaustion** — identify a runaway application pool and safely reduce excess sessions.

Each lab creates a dedicated PostgreSQL database and learner login, provides timed objectives and hints, and grades the live database state with deterministic 100-point checks.

The platform currently includes:

- React/Vite learner UI
- FastAPI orchestration API
- PostgreSQL control + lab databases
- scenario-agnostic runtime routing
- declarative grading engine
- explicit lab teardown
- real PostgreSQL integration tests in GitHub Actions

## Start locally

```bash
cd database-training-platform
docker compose up --build
```

Then open `http://localhost:5173`.

For architecture, scenarios, local connection details and the full roadmap, see the [project README](database-training-platform/README.md).
