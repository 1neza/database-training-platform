# Database Training Platform — PostgreSQL DBA Simulator MVP

A hands-on database training platform where learners operate real PostgreSQL environments under realistic, timed production incidents.

The core product principle is simple: **learn database engineering by doing the job, not by answering database trivia.** Learners receive an isolated database, generated credentials, a production-style incident, objectives and a deadline. They diagnose and modify the real database, then the platform grades the resulting infrastructure state.

## Current MVP

The MVP currently includes:

- nine real PostgreSQL DBA incidents
- selectable React/Vite learner catalog
- lightweight durable learner profile, attempt history and progress
- skill graph, prerequisites and locked/ready/completed learning states
- deterministic recommendations, weak-skill detection and adaptive difficulty targeting
- spaced-repetition review scheduling
- deterministic portfolio/evidence generation
- per-attempt PostgreSQL database and generated learner login
- timed incidents, objectives and hints
- deterministic 100-point grading against live PostgreSQL state
- file-authored, semantically versioned JSON scenarios
- immutable scenario snapshot per attempt
- finish/replay lifecycle with preserved attempt records
- reusable versioned dataset and workload templates
- declarative provisioning and fault injection
- declarative grading rules
- scenario validation CLI enforced in CI
- FastAPI orchestration API
- PostgreSQL control database for attempt/session metadata
- separate PostgreSQL lab server
- Docker Compose local environment
- GitHub Actions with real PostgreSQL integration tests

## Implemented incidents

1. **Slow Checkout Query** — inspect a production lookup plan, add the right composite index and verify PostgreSQL uses it.
2. **Blocked Payment Transaction** — identify and clear a stale row-lock blocker without deleting account data.
3. **Connection Pool Exhaustion** — reduce a runaway application pool to a healthy size while preserving unrelated sessions.
4. **Deadlocking Transfer Procedures** — reproduce and fix inconsistent lock ordering, then prove concurrent execution no longer deadlocks.
5. **Stale Reporting Transaction** — clear an old idle-in-transaction reporting session and preserve the shared e-commerce dataset.
6. **Excessive Analytics Privileges** — audit an analytics role and revoke INSERT/UPDATE/DELETE while preserving required SELECT access.
7. **Failed Deployment Migration** — complete a partial column backfill, enforce NOT NULL, preserve rows and update the migration ledger.
8. **Table Bloat and VACUUM** — diagnose post-delete maintenance state, run safe VACUUM/ANALYZE and preserve all live events.
9. **Logical Backup Restore** — compare live data with a recent logical snapshot and selectively restore only missing rows.

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
2. Review whether it is ready, locked, completed or recommended for the current learner.
3. Start a versioned attempt.
4. Connect to its generated PostgreSQL lab.
5. Diagnose and apply a safe fix.
6. Evaluate the real environment.
7. Review deterministic checks, score and feedback.
8. Finish the attempt to destroy the PostgreSQL runtime while preserving the learning record.
9. Replay when needed; the new attempt is linked to the previous one and uses the current scenario version.

Each attempt stores an immutable snapshot of the scenario definition it began with. If the scenario is later upgraded, an existing attempt still grades against its original definition; a replay intentionally uses the current version.

## Architecture

```text
React / Vite learner UI
          |
       FastAPI
          |
          +---- Platform PostgreSQL
          |       learner profiles / attempts / evaluations
          |
          +---- Learning Engine
          |       skills / prerequisites / recommendations
          |       adaptive difficulty / spaced repetition
          |       portfolio evidence
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

Each scenario declares semantic version, track, skills, prerequisite skills, difficulty, provisioning and evaluation rules. Scenarios reference dataset/workload assets by **slug + exact semantic version**.

Validate authoring changes from `database-training-platform/backend`:

```bash
python -m app.validate_scenarios
```

Validation covers scenario metadata, semantic versions, track references, skill/prerequisite references, difficulty, reusable asset references, provisioning structure, fault references, grading primitives and 100-point totals.

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

Near-term DBA content gaps:

- disk pressure
- replica lag
- failover / disaster recovery

Near-term product gaps:

- authenticated user accounts and account recovery
- learner-facing portfolio API/UI/export
- dedicated weak-area drill scenarios
- stronger production lab isolation and automatic expiry/cleanup

After the PostgreSQL track is broad enough, the platform can expand into data-engineering incidents with Kafka, Debezium CDC, Airflow, streaming data quality and warehouse failures.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the wider roadmap.

## Security note

This remains a local-development MVP. It intentionally gives learners meaningful PostgreSQL permissions inside the training environment. Do not expose the shared lab PostgreSQL server to the public internet.

A production deployment should move each lab into a strong disposable isolation boundary such as a dedicated container/VM or Kubernetes namespace, with network policies, CPU/memory quotas, secret management, automatic expiry/teardown and audited lab actions.
