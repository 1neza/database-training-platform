# Database Training Platform — PostgreSQL DBA Simulator MVP

A hands-on database training platform where learners operate real PostgreSQL environments under realistic, timed production incidents.

The core product principle is simple: **learn database engineering by doing the job, not by answering database trivia.** Learners receive an isolated database, generated credentials, a production-style incident, objectives and a deadline. They diagnose and modify the real database, then the platform grades the resulting infrastructure state.

## Current MVP

The MVP currently includes:

- five real PostgreSQL DBA incidents
- selectable React/Vite learner catalog
- per-attempt PostgreSQL database and generated learner login
- timed incidents, objectives and hints
- deterministic 100-point grading against live PostgreSQL state
- file-authored, semantically versioned JSON scenarios
- immutable scenario snapshot per attempt
- finish/replay lifecycle with preserved attempt records
- reusable versioned dataset templates
- reusable versioned workload templates
- declarative provisioning and fault injection
- declarative grading rules
- scenario validation CLI enforced in CI
- FastAPI orchestration API
- PostgreSQL control database for attempt/session metadata
- separate PostgreSQL lab server
- Docker Compose local environment
- GitHub Actions with real PostgreSQL integration tests

## Implemented incidents

### 1. Slow Checkout Query

An e-commerce `orders` table has grown to hundreds of thousands of rows and a customer checkout lookup is inefficient. The learner inspects the plan, designs the appropriate composite index and verifies PostgreSQL uses it.

This lab reuses `ecommerce-orders-medium@1.0.0` and the named `checkout-customer-history@1.0.0` workload.

### 2. Blocked Payment Transaction

A stale `idle in transaction` application session holds a row lock on a payment account. The learner inspects PostgreSQL activity, identifies the service backend, terminates the correct blocker and verifies writes work again.

### 3. Connection Pool Exhaustion

A runaway checkout service creates twelve PostgreSQL sessions when the expected healthy pool size is three. The learner identifies the offending pool and terminates only the excess connections.

### 4. Deadlocking Transfer Procedures

Two transfer functions acquire the same account rows in opposite order. Provisioning reproduces a real PostgreSQL deadlock before the learner receives the lab. The learner fixes lock ordering and the grader reruns the two paths concurrently.

### 5. Stale Reporting Transaction

A weekly reporting worker finishes its query but leaves a transaction open. The learner finds the old `idle in transaction` session, terminates only the reporting backend and preserves the shared e-commerce dataset.

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

1. Choose an incident from the scenario catalog.
2. Start a versioned attempt.
3. Connect to its generated PostgreSQL lab.
4. Diagnose and apply a safe fix.
5. Evaluate the real environment.
6. Review checks, score and feedback.
7. Finish the attempt to destroy the PostgreSQL runtime while preserving the attempt record.
8. Replay the incident when desired; the replay creates a fresh lab and links the new attempt to the previous one.

Each attempt stores an immutable snapshot of the scenario definition it began with. If the scenario is later upgraded, an existing attempt still grades against its original definition; a replay intentionally uses the current version.

## Architecture

```text
React / Vite learner UI
          |
       FastAPI
          |
          +---- Platform PostgreSQL
          |       durable attempts / evaluations
          |
          +---- Scenario Catalog
          |       backend/scenarios/*.json
          |       semantic versions + validation
          |
          +---- Reusable Asset Catalogs
          |       backend/datasets/*.json
          |       backend/workloads/*.json
          |
          +---- Scenario Engine
          |       declarative provisioning
          |       reusable fault injectors
          |       declarative grading
          |
          +---- Lab PostgreSQL
                  disposable database + learner role per attempt
                  optional generated service roles/sessions
```

## Scenario authoring

Scenario definitions live in `backend/scenarios/*.json`. Reusable assets live in:

- `backend/datasets/*.json`
- `backend/workloads/*.json`

Scenarios reference dataset/workload assets by **slug + exact semantic version**. A scenario definition also declares its own semantic version. When a scenario's behavior, provisioning or grading changes, its version should be bumped.

Validate authoring changes from `database-training-platform/backend`:

```bash
python -m app.validate_scenarios
```

Validation covers scenario metadata, semantic versions, track references, dataset references and versions, workload SQL references and versions, provisioning structure, fault references, grading primitives and 100-point totals.

Current reusable fault primitives:

- persistent idle transaction / row lock
- runaway connection pool
- concurrent deadlock reproduction

Current reusable grading primitives:

- `index_prefix`
- `query_plan_uses_index`
- `row_count`
- `session_count`
- `scalar_equals`
- `query_succeeds`
- `concurrent_sql_no_deadlock`

Current reusable assets:

- dataset: `ecommerce-orders-medium@1.0.0`
- workload: `checkout-customer-history@1.0.0`

## Testing

GitHub Actions validates:

- scenario and reusable-asset references
- Python backend compilation
- backend unit tests
- real PostgreSQL integration tests across all implemented labs
- Vite production frontend build
- Docker Compose configuration

The integration suite provisions incidents through the same generic path used by the API, verifies their initial broken state, performs learner-style remediation and checks the resulting score.

## Reset local state

```bash
docker compose down -v
```

## Next product milestones

The authoring engine is now sufficiently reusable for the MVP. The next product layer is the **learning engine**:

- learner identity/accounts
- persistent attempt-history UI and API
- progress summary per scenario and skill
- skill graph and prerequisites
- scenario recommendations and adaptive difficulty
- evidence/portfolio reports

In parallel, the DBA catalog can grow with disk pressure, VACUUM/table-bloat, permissions, failed migrations, backup/restore, replication lag and failover incidents.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the wider roadmap.

## Security note

This remains a local-development MVP. It intentionally gives learners meaningful PostgreSQL permissions inside the training environment. Do not expose the shared lab PostgreSQL server to the public internet.

A production deployment should move each lab into a strong disposable isolation boundary such as a dedicated container/VM or Kubernetes namespace, with network policies, CPU/memory quotas, secret management, automatic expiry/teardown and audited lab actions.
