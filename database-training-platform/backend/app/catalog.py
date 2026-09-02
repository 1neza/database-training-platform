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
    }
}
