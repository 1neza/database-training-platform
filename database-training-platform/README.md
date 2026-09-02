# Database Training Platform — PostgreSQL DBA Simulator MVP

A runnable MVP for learning database administration by operating a real PostgreSQL database under realistic, timed scenarios.

## What this version includes

- Learning tracks
- Scenario catalogue
- Per-session PostgreSQL database + login
- Realistic generated datasets
- Timed incidents
- Hints
- Deterministic evaluation
- Score + feedback
- React learner dashboard
- FastAPI backend
- PostgreSQL control database
- Separate PostgreSQL lab server
- Docker Compose

The first implemented scenario is **Slow Checkout Query**. The learner receives an e-commerce database containing hundreds of thousands of orders. A production query is slow because an appropriate composite index is missing. The learner must connect to PostgreSQL, diagnose the issue, improve it, and submit the environment for evaluation.

## Run

Requirements:

- Docker Desktop / Docker Engine
- Docker Compose

```bash
docker compose up --build
```

Then open:

- UI: http://localhost:5173
- API docs: http://localhost:8000/docs
- Lab PostgreSQL exposed on localhost:55432

## Example learner flow

1. Open the UI.
2. Choose `PostgreSQL DBA`.
3. Start `Slow Checkout Query`.
4. Copy the generated PostgreSQL credentials.
5. Connect using psql, DBeaver, DataGrip, pgAdmin, etc.
6. Inspect the workload.
7. Apply a safe fix.
8. Click **Evaluate environment**.
9. The backend checks the real PostgreSQL state and calculates a score.

Example connection:

```bash
psql -h localhost -p 55432 -U <generated_user> -d <generated_database>
```

The challenge query is intentionally inefficient until the learner fixes the database.

## Architecture

```text
React UI
   |
FastAPI
   |
   +---- Platform PostgreSQL
   |       users/tracks/scenarios/sessions/results
   |
   +---- Lab PostgreSQL
           one database + role per training session
```

## Why the evaluator is deterministic

AI can later provide explanations, hints, role-play and scenario generation, but pass/fail should not depend only on an LLM. This MVP checks actual database state.

For the first challenge, evaluation checks:

- database is reachable
- the required composite index exists
- index column order is correct
- challenge query receives an indexed query plan

## Useful extension points

The codebase is deliberately structured for these future modules:

- replication lag
- deadlocks
- lock contention
- failed migrations
- connection-pool exhaustion
- disk-pressure incidents
- backup / restore
- permissions
- partitioning
- table bloat
- vacuum tuning
- Kafka / CDC
- MySQL
- cloud database labs
- AI manager / coworker simulation
- bring-your-own-dataset
- company-specific training environments
- interview assessments

## Reset

To delete all local state:

```bash
docker compose down -v
```

## Security note

This is a local-development MVP. It creates database users and returns credentials to the learner. Do not expose the lab PostgreSQL port to the public internet. A production version should use isolated containers/VMs or Kubernetes namespaces, secret management, quotas, network policies and hard teardown boundaries.
