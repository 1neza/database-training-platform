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
        "provisioning": {
            "setup_sql": [
                """
                CREATE TABLE customers (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE orders (
                    id BIGSERIAL PRIMARY KEY,
                    customer_id BIGINT NOT NULL REFERENCES customers(id),
                    status TEXT NOT NULL,
                    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
                    created_at TIMESTAMPTZ NOT NULL
                );
                CREATE TABLE incident_notes (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    note TEXT NOT NULL
                );
                """,
                """
                INSERT INTO customers(email, created_at)
                SELECT 'customer_' || g || '@example.test', now() - (random() * interval '730 days')
                FROM generate_series(1, 15000) AS g;
                """,
                """
                INSERT INTO orders(customer_id, status, total_cents, created_at)
                SELECT
                    1 + floor(random() * 15000)::bigint,
                    (ARRAY['paid','paid','paid','shipped','refunded','pending'])[1 + floor(random()*6)::int],
                    500 + floor(random() * 60000)::int,
                    now() - (random() * interval '365 days')
                FROM generate_series(1, 350000);
                """,
                "CREATE INDEX idx_orders_created_at ON orders(created_at); ANALYZE customers; ANALYZE orders;",
                """
                INSERT INTO incident_notes(note) VALUES
                ('Application query: SELECT id, status, total_cents, created_at FROM orders WHERE customer_id = 4242 ORDER BY created_at DESC LIMIT 20;'),
                ('Do not delete production orders. Changes should be safe for normal application traffic.'),
                ('Your work is evaluated against the actual database state.');
                """,
            ],
            "learner": {
                "statements": [
                    "ALTER TABLE orders OWNER TO {learner}",
                    "ALTER SEQUENCE orders_id_seq OWNER TO {learner}",
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON customers, incident_notes TO {learner}",
                    "GRANT USAGE, SELECT ON SEQUENCE customers_id_seq, incident_notes_id_seq TO {learner}",
                    "GRANT CREATE ON SCHEMA public TO {learner}",
                ]
            },
            "roles": [],
            "faults": [],
        },
        "evaluation": {
            "checks": [
                {
                    "type": "index_prefix",
                    "name": "Composite index exists",
                    "table": "orders",
                    "columns": ["customer_id", "created_at"],
                    "points": 50,
                    "feedback": "Create an index whose leading columns match the filter and ordering pattern, for example customer_id followed by created_at.",
                },
                {
                    "type": "query_plan_uses_index",
                    "name": "Challenge query uses an index",
                    "sql": "SELECT id, status, total_cents, created_at FROM orders WHERE customer_id = 4242 ORDER BY created_at DESC LIMIT 20",
                    "points": 40,
                    "feedback": "The checkout query is still not receiving an indexed plan.",
                },
                {
                    "type": "row_count",
                    "name": "Production data preserved",
                    "table": "orders",
                    "operator": "gte",
                    "expected": 350000,
                    "points": 10,
                    "feedback": "The task must be solved without deleting the production dataset.",
                },
            ],
            "success_feedback": "The environment now has an index aligned with the production lookup pattern, and PostgreSQL can use it for the challenge query.",
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
        "provisioning": {
            "setup_sql": [
                """
                CREATE TABLE accounts (
                    id BIGSERIAL PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    balance_cents BIGINT NOT NULL CHECK (balance_cents >= 0)
                );
                CREATE TABLE incident_notes (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    note TEXT NOT NULL
                );
                INSERT INTO accounts(customer_name, balance_cents)
                VALUES ('Demo Customer', 125000), ('Second Customer', 98000);
                INSERT INTO incident_notes(note) VALUES
                ('A payment update for account id 1 is waiting on a row lock.'),
                ('Look for an unusually old idle-in-transaction session.'),
                ('Do not delete the account or truncate tables to resolve the incident.');
                """
            ],
            "learner": {
                "statements": [
                    "ALTER TABLE accounts OWNER TO {learner}",
                    "ALTER SEQUENCE accounts_id_seq OWNER TO {learner}",
                    "GRANT SELECT ON incident_notes TO {learner}",
                    "GRANT pg_signal_backend TO {learner}",
                    "GRANT pg_read_all_stats TO {learner}",
                ]
            },
            "roles": [
                {
                    "alias": "worker",
                    "prefix": "worker",
                    "statements": [
                        "GRANT CONNECT ON DATABASE {database} TO {role}",
                        "GRANT USAGE ON SCHEMA public TO {role}",
                        "GRANT SELECT, UPDATE ON accounts TO {role}",
                    ],
                }
            ],
            "faults": [
                {
                    "type": "idle_transaction_lock",
                    "role": "worker",
                    "application_name": "legacy-payment-worker",
                    "statements": [
                        "BEGIN",
                        "UPDATE accounts SET balance_cents = balance_cents WHERE id = 1",
                    ],
                }
            ],
        },
        "evaluation": {
            "checks": [
                {
                    "type": "session_count",
                    "name": "Stale blocking transaction cleared",
                    "filters": {"application_name": "legacy-payment-worker", "state": "idle in transaction"},
                    "operator": "eq",
                    "expected": 0,
                    "points": 55,
                    "feedback": "The stale legacy-payment-worker transaction is still open. Identify its PID and terminate that backend safely.",
                },
                {
                    "type": "row_count",
                    "name": "Account data preserved",
                    "table": "accounts",
                    "operator": "eq",
                    "expected": 2,
                    "points": 20,
                    "feedback": "Production-style account data must remain intact; deleting rows is not a valid incident response.",
                },
                {
                    "type": "query_succeeds",
                    "name": "Affected payment row is writable",
                    "sql": "UPDATE accounts SET balance_cents = balance_cents WHERE id = 1",
                    "lock_timeout_ms": 500,
                    "points": 25,
                    "feedback": "The affected account row is still locked by another transaction.",
                },
            ],
            "success_feedback": "The blocking transaction is gone, the account data is intact, and normal writes can proceed again.",
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
        "provisioning": {
            "setup_sql": [
                """
                CREATE TABLE service_config (
                    id INTEGER PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    expected_pool_size INTEGER NOT NULL CHECK (expected_pool_size > 0)
                );
                CREATE TABLE incident_notes (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    note TEXT NOT NULL
                );
                INSERT INTO service_config(id, service_name, expected_pool_size)
                VALUES (1, 'checkout-api', 3);
                INSERT INTO incident_notes(note) VALUES
                ('The checkout API normally keeps no more than three idle database sessions.'),
                ('The incident was triggered by a runaway application connection pool.'),
                ('Do not terminate unrelated administrative or learner sessions.');
                """
            ],
            "learner": {
                "statements": [
                    "GRANT SELECT ON service_config, incident_notes TO {learner}",
                    "GRANT pg_signal_backend TO {learner}",
                    "GRANT pg_read_all_stats TO {learner}",
                ]
            },
            "roles": [
                {
                    "alias": "pool",
                    "prefix": "pool",
                    "statements": ["GRANT CONNECT ON DATABASE {database} TO {role}"],
                }
            ],
            "faults": [
                {
                    "type": "connection_pool",
                    "role": "pool",
                    "application_name": "checkout-api-pool",
                    "count": 12,
                    "warmup_sql": "SELECT 1",
                }
            ],
        },
        "evaluation": {
            "checks": [
                {
                    "type": "session_count",
                    "name": "Runaway checkout pool reduced",
                    "filters": {"application_name": "checkout-api-pool"},
                    "operator": "lte",
                    "expected": 3,
                    "points": 65,
                    "feedback": "The checkout API still has too many sessions. Identify only the checkout-api-pool backends and reduce the pool to three or fewer.",
                },
                {
                    "type": "scalar_equals",
                    "name": "Service configuration preserved",
                    "sql": "SELECT expected_pool_size FROM service_config WHERE id = 1 AND service_name = 'checkout-api'",
                    "expected": 3,
                    "points": 20,
                    "feedback": "The incident should be mitigated by handling database sessions, not by deleting or corrupting the service configuration.",
                },
                {
                    "type": "scalar_equals",
                    "name": "Database remains responsive",
                    "sql": "SELECT 1",
                    "expected": 1,
                    "points": 15,
                    "feedback": "The database is not responding normally after the attempted mitigation.",
                },
            ],
            "success_feedback": "Connection pressure is back within the expected pool size, configuration is intact, and the database remains responsive.",
        },
    },
    "deadlock-transfer-procedures": {
        "slug": "deadlock-transfer-procedures",
        "track_slug": "postgresql-dba",
        "title": "Deadlocking Transfer Procedures",
        "level": "intermediate-advanced",
        "duration_minutes": 40,
        "summary": "Two payment procedures lock account rows in opposite order, causing PostgreSQL to abort one transaction with a deadlock.",
        "incident": (
            "18:05 — Payment workers intermittently fail with PostgreSQL deadlock errors during opposing transfers. "
            "The failure is reproducible under concurrency. Find the inconsistent lock ordering, implement a safe database-side fix, and prove both transfer paths can run concurrently."
        ),
        "objectives": [
            "Inspect the recorded incident evidence and transfer function definitions.",
            "Explain why opposite row-lock ordering can create a deadlock cycle.",
            "Modify the database functions so both paths acquire locks consistently.",
            "Verify concurrent execution completes without SQLSTATE 40P01.",
            "Preserve the account dataset and total balance.",
        ],
        "hints": [
            "Use pg_get_functiondef(...) to inspect both transfer functions.",
            "Compare the order in which account ids 1 and 2 are selected FOR UPDATE.",
            "Deadlocks are prevented when competing transactions acquire shared resources in a consistent order.",
        ],
        "provisioning": {
            "setup_sql": [
                """
                CREATE TABLE transfer_accounts (
                    id INTEGER PRIMARY KEY,
                    owner_name TEXT NOT NULL,
                    balance_cents BIGINT NOT NULL CHECK (balance_cents >= 0)
                );
                CREATE TABLE incident_events (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL
                );
                INSERT INTO transfer_accounts(id, owner_name, balance_cents)
                VALUES (1, 'Primary Wallet', 100000), (2, 'Reserve Wallet', 100000);
                """,
                """
                CREATE OR REPLACE FUNCTION transfer_forward() RETURNS void
                LANGUAGE plpgsql SECURITY DEFINER AS $$
                BEGIN
                    PERFORM 1 FROM transfer_accounts WHERE id = 1 FOR UPDATE;
                    PERFORM pg_sleep(0.25);
                    PERFORM 1 FROM transfer_accounts WHERE id = 2 FOR UPDATE;
                    UPDATE transfer_accounts SET balance_cents = balance_cents - 100 WHERE id = 1;
                    UPDATE transfer_accounts SET balance_cents = balance_cents + 100 WHERE id = 2;
                END;
                $$;
                CREATE OR REPLACE FUNCTION transfer_reverse() RETURNS void
                LANGUAGE plpgsql SECURITY DEFINER AS $$
                BEGIN
                    PERFORM 1 FROM transfer_accounts WHERE id = 2 FOR UPDATE;
                    PERFORM pg_sleep(0.25);
                    PERFORM 1 FROM transfer_accounts WHERE id = 1 FOR UPDATE;
                    UPDATE transfer_accounts SET balance_cents = balance_cents - 100 WHERE id = 2;
                    UPDATE transfer_accounts SET balance_cents = balance_cents + 100 WHERE id = 1;
                END;
                $$;
                """,
            ],
            "learner": {
                "statements": [
                    "ALTER TABLE transfer_accounts OWNER TO {learner}",
                    "ALTER FUNCTION transfer_forward() OWNER TO {learner}",
                    "ALTER FUNCTION transfer_reverse() OWNER TO {learner}",
                    "GRANT SELECT ON incident_events TO {learner}",
                ]
            },
            "roles": [
                {
                    "alias": "transfer_worker",
                    "prefix": "transfer_worker",
                    "statements": [
                        "GRANT CONNECT ON DATABASE {database} TO {role}",
                        "GRANT USAGE ON SCHEMA public TO {role}",
                        "GRANT EXECUTE ON FUNCTION transfer_forward() TO {role}",
                        "GRANT EXECUTE ON FUNCTION transfer_reverse() TO {role}",
                    ],
                }
            ],
            "faults": [
                {
                    "type": "concurrent_deadlock_probe",
                    "role": "transfer_worker",
                    "application_name": "payment-transfer-worker",
                    "statements": ["SELECT transfer_forward()", "SELECT transfer_reverse()"],
                    "event_sql": "INSERT INTO incident_events(event_type, detail) VALUES ('deadlock', 'Concurrent transfer_forward() and transfer_reverse() reproduced SQLSTATE 40P01 during incident setup.')",
                }
            ],
        },
        "evaluation": {
            "checks": [
                {
                    "type": "concurrent_sql_no_deadlock",
                    "name": "Concurrent transfer paths no longer deadlock",
                    "statements": ["SELECT transfer_forward()", "SELECT transfer_reverse()"],
                    "points": 65,
                    "feedback": "The two transfer paths still form a deadlock cycle under concurrent execution. Make their row-lock ordering consistent.",
                },
                {
                    "type": "row_count",
                    "name": "Account rows preserved",
                    "table": "transfer_accounts",
                    "operator": "eq",
                    "expected": 2,
                    "points": 15,
                    "feedback": "Both production-style transfer account rows must remain present.",
                },
                {
                    "type": "scalar_equals",
                    "name": "Total balance preserved",
                    "sql": "SELECT sum(balance_cents) FROM transfer_accounts",
                    "expected": 200000,
                    "points": 20,
                    "feedback": "The fix must preserve the total balance across both accounts.",
                },
            ],
            "success_feedback": "Both transfer paths now complete concurrently without a deadlock, while the account set and total balance remain intact.",
        },
    },
}
