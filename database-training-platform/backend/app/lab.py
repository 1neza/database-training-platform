import re
import secrets
from dataclasses import dataclass

import asyncpg

from .config import settings


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def ident(value: str) -> str:
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError("Unsafe PostgreSQL identifier")
    return '"' + value + '"'


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass
class LabCredentials:
    database: str
    username: str
    password: str


async def _admin_connect(database: str = "postgres"):
    return await asyncpg.connect(
        host=settings.lab_admin_host,
        port=settings.lab_admin_port,
        user=settings.lab_admin_user,
        password=settings.lab_admin_password,
        database=database,
    )


async def provision_slow_checkout(session_short_id: str) -> LabCredentials:
    database = f"lab_{session_short_id}"
    username = f"student_{session_short_id}"
    password = secrets.token_urlsafe(18)

    admin = await _admin_connect()
    try:
        await admin.execute(
            f"CREATE ROLE {ident(username)} LOGIN PASSWORD {literal(password)}"
        )
        await admin.execute(f"CREATE DATABASE {ident(database)} OWNER {ident(username)}")
    finally:
        await admin.close()

    conn = await _admin_connect(database)
    try:
        await conn.execute(f"GRANT ALL ON SCHEMA public TO {ident(username)}")

        await conn.execute("""
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
        """)

        await conn.execute("""
            INSERT INTO customers(email, created_at)
            SELECT
                'customer_' || g || '@example.test',
                now() - (random() * interval '730 days')
            FROM generate_series(1, 15000) AS g;
        """)

        await conn.execute("""
            INSERT INTO orders(customer_id, status, total_cents, created_at)
            SELECT
                1 + floor(random() * 15000)::bigint,
                (ARRAY['paid','paid','paid','shipped','refunded','pending'])[1 + floor(random()*6)::int],
                500 + floor(random() * 60000)::int,
                now() - (random() * interval '365 days')
            FROM generate_series(1, 350000);
        """)

        await conn.execute("""
            CREATE INDEX idx_orders_created_at ON orders(created_at);
            ANALYZE customers;
            ANALYZE orders;
        """)

        await conn.execute("""
            INSERT INTO incident_notes(note) VALUES
            ('Application query: SELECT id, status, total_cents, created_at FROM orders WHERE customer_id = 4242 ORDER BY created_at DESC LIMIT 20;'),
            ('Do not delete production orders. Changes should be safe for normal application traffic.'),
            ('Your work is evaluated against the actual database state.');
        """)

        # The learner must own the target table to create/drop indexes during the DBA lab.
        # We preserve the other tables as admin-owned reference/support objects.
        await conn.execute(f"ALTER TABLE orders OWNER TO {ident(username)}")
        await conn.execute(f"ALTER SEQUENCE orders_id_seq OWNER TO {ident(username)}")

        await conn.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON customers, incident_notes TO {ident(username)};
            GRANT USAGE, SELECT ON SEQUENCE customers_id_seq, incident_notes_id_seq TO {ident(username)};
            GRANT CREATE ON SCHEMA public TO {ident(username)};
        """)
    finally:
        await conn.close()

    return LabCredentials(database=database, username=username, password=password)


async def connect_as_admin(database: str):
    return await _admin_connect(database)


async def teardown_lab(database: str, username: str):
    admin = await _admin_connect()
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            database,
        )
        await admin.execute(f"DROP DATABASE IF EXISTS {ident(database)}")
        await admin.execute(f"DROP ROLE IF EXISTS {ident(username)}")
    finally:
        await admin.close()
