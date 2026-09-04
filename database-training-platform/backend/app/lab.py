import re
import secrets
from dataclasses import dataclass

import asyncpg

from .config import settings


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_BLOCKERS: dict[str, asyncpg.Connection] = {}


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


async def _create_lab_identity(session_short_id: str) -> LabCredentials:
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

    return LabCredentials(database=database, username=username, password=password)


async def provision_slow_checkout(session_short_id: str) -> LabCredentials:
    creds = await _create_lab_identity(session_short_id)
    username = creds.username

    conn = await _admin_connect(creds.database)
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

        await conn.execute(f"ALTER TABLE orders OWNER TO {ident(username)}")
        await conn.execute(f"ALTER SEQUENCE orders_id_seq OWNER TO {ident(username)}")

        await conn.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON customers, incident_notes TO {ident(username)};
            GRANT USAGE, SELECT ON SEQUENCE customers_id_seq, incident_notes_id_seq TO {ident(username)};
            GRANT CREATE ON SCHEMA public TO {ident(username)};
        """)
    finally:
        await conn.close()

    return creds


async def provision_blocked_payment(session_short_id: str) -> LabCredentials:
    creds = await _create_lab_identity(session_short_id)
    username = creds.username

    conn = await _admin_connect(creds.database)
    try:
        await conn.execute("""
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
        """)

        await conn.execute(f"ALTER TABLE accounts OWNER TO {ident(username)}")
        await conn.execute(f"ALTER SEQUENCE accounts_id_seq OWNER TO {ident(username)}")
        await conn.execute(f"""
            GRANT SELECT ON incident_notes TO {ident(username)};
            GRANT pg_signal_backend TO {ident(username)};
            GRANT pg_read_all_stats TO {ident(username)};
        """)
    finally:
        await conn.close()

    blocker = await _admin_connect(creds.database)
    await blocker.execute("SET application_name = 'legacy-payment-worker'")
    await blocker.execute("BEGIN")
    await blocker.execute("UPDATE accounts SET balance_cents = balance_cents WHERE id = 1")
    _BLOCKERS[creds.database] = blocker

    return creds


async def connect_as_admin(database: str):
    return await _admin_connect(database)


async def teardown_lab(database: str, username: str):
    blocker = _BLOCKERS.pop(database, None)
    if blocker is not None and not blocker.is_closed():
        await blocker.close()

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
