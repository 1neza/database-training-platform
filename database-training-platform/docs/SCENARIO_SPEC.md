# Scenario Authoring Specification

Scenario definitions live in `backend/scenarios/*.json`. The loader discovers them automatically; API routing remains scenario-agnostic.

Each filename must match the scenario slug, and every scenario declares a semantic version:

```json
{
  "slug": "slow-checkout-query",
  "version": "1.2.0"
}
```

Versions use `MAJOR.MINOR.PATCH`. Bump the scenario version when provisioning, learner behavior, workload references or grading semantics change.

## Scenario structure

A scenario contains:

- learner-facing metadata
- provisioning specification
- optional references to versioned reusable datasets
- generated roles and fault definitions
- deterministic evaluation checks
- optional references to versioned named workloads

Example:

```json
{
  "slug": "slow-checkout-query",
  "version": "1.2.0",
  "track_slug": "postgresql-dba",
  "title": "Slow Checkout Query",
  "level": "beginner-intermediate",
  "duration_minutes": 45,
  "summary": "Checkout latency increased after the orders table grew.",
  "incident": "Checkout requests are taking several seconds...",
  "objectives": ["Inspect the plan", "Apply a safe fix", "Verify recovery"],
  "hints": ["Inspect existing indexes."],
  "provisioning": {
    "datasets": [
      {"slug": "ecommerce-orders-medium", "version": "1.0.0"}
    ],
    "setup_sql": ["CREATE TABLE incident_notes (...);"],
    "learner": {
      "statements": ["ALTER TABLE orders OWNER TO {learner}"]
    },
    "roles": [],
    "faults": []
  },
  "evaluation": {
    "checks": [
      {
        "type": "query_plan_uses_index",
        "name": "Challenge query uses an index",
        "sql_ref": {
          "workload": "checkout-customer-history",
          "version": "1.0.0",
          "statement": "recent_orders"
        },
        "points": 100
      }
    ]
  }
}
```

## Required metadata

Every scenario must provide:

- `slug`
- `version`
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

The referenced track must exist in the platform track catalog.

## Dataset templates

Reusable datasets live in `backend/datasets/*.json` and are referenced by exact slug/version pairs.

Current example:

```json
{
  "slug": "ecommerce-orders-medium",
  "version": "1.0.0",
  "setup_sql": ["CREATE TABLE ...", "INSERT ..."]
}
```

A scenario can reference it with:

```json
"datasets": [
  {"slug": "ecommerce-orders-medium", "version": "1.0.0"}
]
```

Dataset SQL runs before scenario-specific `setup_sql`. This allows several incidents to reuse the same realistic data model while keeping incident-specific setup small.

## Provisioning

Scenario `setup_sql` is executed after referenced dataset templates.

`learner.statements` can use:

- `{learner}` — safely quoted generated learner role
- `{database}` — safely quoted generated lab database

Generated service-role statements can also use:

- `{role}` — safely quoted generated service role

### Service roles

Each `roles` entry defines:

- `alias` — stable identifier referenced by faults
- `prefix` — generated PostgreSQL role-name prefix
- `statements` — grants/setup for the generated role

Generated role names/passwords are unique to a lab and removed during teardown.

### Fault primitives

#### `idle_transaction_lock`

Keeps a generated service connection open after configured statements. It can model either a row-lock blocker or a stale read-only transaction.

#### `connection_pool`

Creates a configured number of persistent application sessions sharing an `application_name`.

#### `concurrent_deadlock_probe`

Runs two configured SQL paths concurrently and requires PostgreSQL to reproduce `SQLSTATE 40P01`. Optional `event_sql` can record incident evidence.

## Workload templates

Reusable named SQL workloads live in `backend/workloads/*.json`.

Example:

```json
{
  "slug": "checkout-customer-history",
  "version": "1.0.0",
  "statements": {
    "recent_orders": "SELECT ..."
  }
}
```

Evaluation checks that normally accept `sql` can instead use:

```json
"sql_ref": {
  "workload": "checkout-customer-history",
  "version": "1.0.0",
  "statement": "recent_orders"
}
```

This keeps canonical application SQL in one reusable place and allows future load generators to reuse the same named workload.

## Evaluation

Every evaluation check has positive points and all checks must total exactly 100.

Supported grading primitives:

- `index_prefix`
- `query_plan_uses_index`
- `row_count`
- `session_count`
- `scalar_equals`
- `query_succeeds`
- `concurrent_sql_no_deadlock`

Checks accepting SQL can use inline `sql` or a supported `sql_ref`, but not both.

## Attempt versioning and replay

When an attempt starts, the backend stores an immutable snapshot of the complete scenario definition inside the attempt record. This protects historical grading semantics if the live scenario file later changes.

- finishing an attempt destroys its PostgreSQL runtime but preserves the attempt/evaluation record
- replay creates a fresh attempt linked to the previous attempt
- replay intentionally uses the current scenario version
- the previous attempt remains associated with the exact scenario snapshot it originally used

## Validation workflow

From `database-training-platform/backend` run:

```bash
python -m app.validate_scenarios
```

Validation checks:

1. JSON loading and filename/slug consistency.
2. Required metadata and semantic versions.
3. Track references.
4. Dataset references and exact versions.
5. Provisioning structure and service-role/fault references.
6. Workload SQL references and exact versions.
7. Supported grading primitives and 100-point totals.

GitHub Actions repeats validation before compilation and real PostgreSQL integration tests.
