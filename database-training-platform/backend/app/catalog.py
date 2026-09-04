TRACKS = [
    {
        "slug": "postgresql-dba",
        "name": "PostgreSQL DBA",
        "description": "Operate PostgreSQL like a production database administrator: performance, reliability, access, recovery and incident response.",
    },
    {
        "slug": "sql-performance",
        "name": "SQL Performance",
        "description": "Diagnose query plans, indexes, joins, cardinality and production SQL regressions.",
    },
    {
        "slug": "database-design",
        "name": "Database Design",
        "description": "Model scalable relational systems with constraints, indexing, partitioning and safe evolution.",
    },
]

SCENARIOS = {
    "slow-checkout-query": {
        "slug": "slow-checkout-query",
        "track_slug": "postgresql-dba",
        "title": "Slow Checkout Query",
        "level": "beginner-intermediate",
        "duration_minutes": 45,
        "summary": "Checkout latency increased after the orders table grew. Diagnose and safely improve the database.",
        "incident": (
            "09:10 — Customer support reports checkout requests taking several seconds. "
            "The engineering manager says the issue appeared as order volume grew. "
            "You have 45 minutes to diagnose the database and implement a safe production-ready fix."
        ),
        "objectives": [
            "Inspect the schema and data volume.",
            "Run EXPLAIN or EXPLAIN ANALYZE on the checkout lookup query.",
            "Identify why PostgreSQL is scanning too much data.",
            "Apply a database-level optimization without deleting data.",
            "Verify the query plan improved.",
        ],
        "hints": [
            "Start with \\d orders and inspect existing indexes.",
            "The application frequently filters by customer_id and asks for the newest orders.",
            "A useful index can serve both filtering and ordering when its column order matches the query.",
        ],
        "runtime": {
            "provisioner": "slow_checkout",
            "evaluator": "slow_checkout",
        },
    },
    "blocked-payment-transaction": {
        "slug": "blocked-payment-transaction",
        "track_slug": "postgresql-dba",
        "title": "Blocked Payment Transaction",
        "level": "intermediate",
        "duration_minutes": 35,
        "summary": "A stale transaction is holding a row lock and payment updates are piling up behind it.",
        "incident": (
            "14:25 — The payments API is timing out for one customer. Monitoring shows an UPDATE waiting on a row lock. "
            "Find the blocking session, determine whether it is safe to stop, and restore normal transaction flow without deleting data."
        ),
        "objectives": [
            "Inspect pg_stat_activity and pg_locks.",
            "Identify the blocking backend and the transaction it is holding open.",
            "Clear the blocker safely.",
            "Verify no sessions remain blocked on the affected payment row.",
        ],
        "hints": [
            "pg_blocking_pids(pid) can tell you which backend is blocking another session.",
            "Look for a session that is idle in transaction and has been open much longer than expected.",
            "This lab grants the learner permission to signal backends inside the isolated training server.",
        ],
        "runtime": {
            "provisioner": "blocked_payment",
            "evaluator": "blocked_payment",
        },
    },
    "connection-pool-exhaustion": {
        "slug": "connection-pool-exhaustion",
        "track_slug": "postgresql-dba",
        "title": "Connection Pool Exhaustion",
        "level": "intermediate",
        "duration_minutes": 30,
        "summary": "A runaway application pool opened far more PostgreSQL sessions than expected and is consuming connection capacity.",
        "incident": (
            "16:40 — New API requests intermittently fail to obtain a database connection. "
            "The checkout service has accumulated an abnormal number of idle sessions. "
            "Identify the offending pool, reduce connection pressure safely, and verify the database can still accept fresh work."
        ),
        "objectives": [
            "Inspect pg_stat_activity and group sessions by application_name/state.",
            "Identify the runaway checkout API pool.",
            "Reduce unnecessary sessions without damaging application data.",
            "Verify healthy connection capacity remains available.",
        ],
        "hints": [
            "Group pg_stat_activity by application_name and state before killing anything.",
            "The abnormal sessions all share the same application_name.",
            "The target is to leave a small healthy pool rather than terminate every database session indiscriminately.",
        ],
        "runtime": {
            "provisioner": "connection_pressure",
            "evaluator": "connection_pressure",
        },
    },
}
