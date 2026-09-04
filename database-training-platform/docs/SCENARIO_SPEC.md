# Scenario Authoring Specification

Scenario definitions live in `backend/scenarios/*.json`. `backend/app/catalog.py` only discovers and loads those files; the API remains scenario-agnostic.

Each file name must match its scenario slug. For example:

```text
backend/scenarios/connection-pool-exhaustion.json
```

must contain:

```json
{
  "slug": "connection-pool-exhaustion"
}
```

A simplified scenario looks like this:

```json
{
  "slug": "connection-pool-exhaustion",
  "track_slug": "postgresql-dba",
  "title": "Connection Pool Exhaustion",
  "level": "intermediate",
  "duration_minutes": 30,
  "summary": "A runaway application pool opened too many sessions.",
  "incident": "New API requests intermittently fail...",
  "objectives": ["Inspect activity", "Reduce pressure", "Verify recovery"],
  "hints": ["Group pg_stat_activity by application_name."],
  "provisioning": {
    "setup_sql": [
      "CREATE TABLE service_config (...);",
      "INSERT INTO service_config (...) VALUES (...);"
    ],
    "learner": {
      "statements": [
        "GRANT SELECT ON service_config TO {learner}",
        "GRANT pg_signal_backend TO {learner}"
      ]
    },
    "roles": [
      {
        "alias": "pool",
        "prefix": "pool",
        "statements": [
          "GRANT CONNECT ON DATABASE {database} TO {role}"
        ]
      }
    ],
    "faults": [
      {
        "type": "connection_pool",
        "role": "pool",
        "application_name": "checkout-api-pool",
        "count": 12,
        "warmup_sql": "SELECT 1"
      }
    ]
  },
  "evaluation": {
    "checks": [
      {
        "type": "session_count",
        "name": "Runaway pool reduced",
        "filters": {"application_name": "checkout-api-pool"},
        "operator": "lte",
        "expected": 3,
        "points": 65
      },
      {
        "type": "scalar_equals",
        "name": "Database remains responsive",
        "sql": "SELECT 1",
        "expected": 1,
        "points": 35
      }
    ],
    "success_feedback": "Connection pressure is back within the expected range."
  }
}
```

## Required metadata

Every scenario must provide:

- `slug`
- `track_slug`
- `title`
- `level`
- positive integer `duration_minutes`
- `summary`
- `incident`
- non-empty `objectives`
- non-empty `hints`
- `provisioning`
- `evaluation`

The referenced `track_slug` must exist in the platform track catalog.

## Provisioning

`setup_sql` is executed in order by the lab administrator inside the newly created per-session database.

`learner.statements` can use these trusted placeholders:

- `{learner}` — safely quoted generated learner role
- `{database}` — safely quoted generated lab database

Generated service-role statements can also use:

- `{role}` — safely quoted generated service role

### Service roles

Each entry in `roles` defines:

- `alias` — stable name used by fault definitions
- `prefix` — prefix for the generated PostgreSQL role name
- `statements` — grants/setup executed for that role

Passwords and concrete role names are generated per lab and removed during teardown.

### Supported fault primitives

#### `idle_transaction_lock`

Keeps a generated service connection open after running configured statements such as `BEGIN` and an `UPDATE`. Used by the blocked-payment lab.

#### `connection_pool`

Creates a configured number of persistent service sessions with a shared `application_name`. Used by the connection-exhaustion lab.

#### `concurrent_deadlock_probe`

Runs exactly two SQL statements concurrently through a generated non-superuser service role and requires PostgreSQL to produce a real deadlock (`SQLSTATE 40P01`). Optional `event_sql` records evidence after reproduction. Used by the deadlocking-transfer lab.

## Evaluation

Every evaluation check has a positive point value, and configured checks must total exactly 100 points.

Supported grading primitives:

- `index_prefix`
- `query_plan_uses_index`
- `row_count`
- `session_count`
- `scalar_equals`
- `query_succeeds`
- `concurrent_sql_no_deadlock`

`concurrent_sql_no_deadlock` opens two independent administrator connections, executes the configured statements concurrently and fails when PostgreSQL returns `40P01` or another database error.

## Validation workflow

Run this from `database-training-platform/backend` before committing a scenario:

```bash
python -m app.validate_scenarios
```

The validator checks file loading, filename/slug consistency, required metadata, track references, provisioning structure, service-role/fault references, supported grading checks and the 100-point score total.

GitHub Actions runs the same validator before backend compilation and the live PostgreSQL integration suite. This gives scenario changes three gates:

1. JSON loading.
2. Static scenario validation.
3. Runtime PostgreSQL tests.

## Next authoring steps

The next improvements are scenario versioning, reset/replay, and reusable named dataset/workload templates so scenario JSON becomes smaller and easier to compose.
