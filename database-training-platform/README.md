# Database Training Platform — PostgreSQL DBA Simulator MVP

A hands-on database training platform where learners operate real PostgreSQL environments under realistic, timed production incidents.

The core product principle is simple: **learn database engineering by doing the job, not by answering database trivia.** Learners receive an isolated database, generated credentials, a production-style incident, objectives and a deadline. They diagnose and modify the real database, then the platform grades the resulting infrastructure state.

## Current MVP

The MVP currently includes:

- PostgreSQL DBA scenario catalog and selectable learner UI
- per-session PostgreSQL database and generated learner login
- realistic synthetic datasets and generated application/service roles
- timed incidents, objectives and hints
- deterministic 100-point grading against the live database
- declarative scenario provisioning and reusable fault injection
- declarative scenario evaluation rules
- explicit lab teardown and return-to-catalog flow
- React + Vite learner dashboard
- FastAPI orchestration API
- PostgreSQL control database for session metadata
- separate PostgreSQL lab server
- Docker Compose local environment
- GitHub Actions with real PostgreSQL integration tests

## Implemented incidents

### 1. Slow Checkout Query

An e-commerce `orders` table has grown to hundreds of thousands of rows and a customer checkout lookup is inefficient. The learner inspects the plan, designs the appropriate composite index and verifies PostgreSQL uses it.

Grading checks include:
- composite index prefix
- indexed query plan
- production data preservation

### 2. Blocked Payment Transaction

A stale `idle in transaction` application session holds a row lock on a payment account. The learner inspects PostgreSQL activity, identifies the non-superuser service backend, terminates the correct blocker and verifies writes work again.

Grading checks include:
- stale blocking session removed
- account data preserved
- affected row writable within the lock timeout

### 3. Connection Pool Exhaustion

A runaway checkout service creates twelve PostgreSQL sessions when the expected healthy pool size is three. The learner groups sessions by application, identifies the offending pool and terminates only the excess connections.

Grading checks include:
- checkout pool reduced to three or fewer sessions
- service configuration preserved
- database remains responsive

### 4. Deadlocking Transfer Procedures

Two payment transfer functions acquire row locks on the same pair of accounts in opposite order. Provisioning executes both paths concurrently and requires PostgreSQL to reproduce a real `deadlock detected` failure before the learner receives the lab. The learner inspects the functions, makes lock acquisition order consistent and submits the environment for a concurrent replay.

Grading checks include:
- both transfer paths complete concurrently without SQLSTATE `40P01`
- both account rows remain present
- total account balance remains unchanged

## Run locally

From this project directory:

```bash
docker compose up --build
```

Open:

- Learner UI: `http://localhost:5173`
- FastAPI docs: `http://localhost:8000/docs`
- Lab PostgreSQL: `localhost:55432`

Example learner connection:

```bash
psql -h localhost -p 55432 -U <generated_user> -d <generated_database>
```

## Learner flow

1. Open the learner UI.
2. Choose an incident from the PostgreSQL DBA scenario catalog.
3. Start the lab.
4. Copy the generated PostgreSQL connection credentials.
5. Diagnose the incident using `psql`, DBeaver, DataGrip, pgAdmin or another PostgreSQL client.
6. Apply a safe fix to the real lab environment.
7. Click **Evaluate environment**.
8. Review the objective checks, score and feedback.
9. Finish the lab; the platform tears down its database and generated roles and returns to the catalog.

## Architecture

```text
React / Vite learner UI
          |
       FastAPI
          |
          +---- Platform PostgreSQL
          |       session metadata / results
          |
          +---- Scenario Engine
          |       declarative provisioning engine
          |       reusable fault injectors
          |       declarative grading engine
          |
          +---- Lab PostgreSQL
                  database + learner role per session
                  optional generated service roles/sessions
```

### Scenario engine

Scenario definitions live in `backend/app/catalog.py`. API routing is scenario-agnostic: each scenario contains provisioning and evaluation specifications as data rather than requiring API-specific branching.

Provisioning currently supports:

- ordered setup SQL
- learner ownership/grant statements
- generated non-superuser service roles
- persistent `idle in transaction` row-lock injection
- runaway connection-pool injection
- concurrent deadlock reproduction with incident evidence
- generic runtime connection and role teardown

Reusable grading primitives currently include:

- `index_prefix`
- `query_plan_uses_index`
- `row_count`
- `session_count`
- `scalar_equals`
- `query_succeeds`
- `concurrent_sql_no_deadlock`

Each scenario's checks must total 100 points. Application startup validates the complete catalog and fails fast on invalid provisioning references, unsupported fault types, unsupported grading checks or incorrect point totals.

This keeps the AI layer optional. An LLM can later act as a manager, coworker, mentor or postmortem reviewer, but the technical pass/fail decision is grounded in PostgreSQL state and repeatable workloads.

## Testing

GitHub Actions validates:

- Python backend compilation
- backend unit tests
- real PostgreSQL integration tests
- Vite production frontend build
- Docker Compose configuration

The integration suite provisions every implemented incident through the same generic scenario path used by the API, confirms the initial environment fails grading, performs the expected learner-style remediation and verifies the environment reaches 100/100 before teardown.

The deadlock integration test also confirms the database actually emits a PostgreSQL deadlock between `transfer_forward()` and `transfer_reverse()` before the learner fix.

## Reset local state

```bash
docker compose down -v
```

## Next product milestones

Near-term priorities are:

- move scenario definitions from the Python catalog into validated YAML/JSON files
- add scenario reset/replay and versioning
- more DBA incidents: long-running transactions, permissions, failed migrations, backup/restore, disk pressure and VACUUM/bloat
- persistent learner progress and skill graph
- scenario prerequisites and adaptive recommendations
- stronger per-lab isolation using disposable containers or namespaces
- AI manager/coworker simulation and incident debriefs
- data-engineering tracks with Kafka, Debezium CDC and pipeline incidents
- company onboarding and technical hiring modes

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the wider roadmap.

## Security note

This remains a local-development MVP. It intentionally gives learners meaningful PostgreSQL permissions inside the training environment. Do not expose the shared lab PostgreSQL server to the public internet.

A production deployment should move each lab into a strong disposable isolation boundary such as a dedicated container/VM or Kubernetes namespace, with network policies, CPU/memory quotas, secret management, automatic expiry and teardown, and audited lab actions.
