import re
import secrets
from dataclasses import dataclass

import asyncpg

from .config import settings


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_RUNTIME_CONNECTIONS: dict[str, list[asyncpg.Connection]] = {}
_RUNTIME_ROLES: dict[str, set[str]] = {}


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


async def admin_connect(database: str = "postgres"):
    return await asyncpg.connect(
        host=settings.lab_admin_host,
        port=settings.lab_admin_port,
        user=settings.lab_admin_user,
        password=settings.lab_admin_password,
        database=database,
    )


async def role_connect(database: str, username: str, password: str):
    return await asyncpg.connect(
        host=settings.lab_admin_host,
        port=settings.lab_admin_port,
        user=username,
        password=password,
        database=database,
    )


def terminate_connection_quietly(conn: asyncpg.Connection) -> None:
    if conn.is_closed():
        return
    try:
        conn.terminate()
    except Exception:
        pass


async def create_login_role(role: str, password: str) -> None:
    admin = await admin_connect()
    try:
        await admin.execute(
            f"CREATE ROLE {ident(role)} LOGIN PASSWORD {literal(password)}"
        )
    finally:
        await admin.close()


def register_runtime_role(database: str, role: str) -> None:
    _RUNTIME_ROLES.setdefault(database, set()).add(role)


def register_runtime_connection(database: str, conn: asyncpg.Connection) -> None:
    _RUNTIME_CONNECTIONS.setdefault(database, []).append(conn)


async def create_lab_identity(session_short_id: str) -> LabCredentials:
    database = f"lab_{session_short_id}"
    username = f"student_{session_short_id}"
    password = secrets.token_urlsafe(18)

    admin = await admin_connect()
    try:
        await admin.execute(
            f"CREATE ROLE {ident(username)} LOGIN PASSWORD {literal(password)}"
        )
        await admin.execute(f"CREATE DATABASE {ident(database)} OWNER {ident(username)}")
    finally:
        await admin.close()

    return LabCredentials(database=database, username=username, password=password)


async def connect_as_admin(database: str):
    return await admin_connect(database)


async def teardown_lab(database: str, username: str):
    for runtime_conn in _RUNTIME_CONNECTIONS.pop(database, []):
        terminate_connection_quietly(runtime_conn)

    runtime_roles = sorted(_RUNTIME_ROLES.pop(database, set()))

    admin = await admin_connect()
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            database,
        )
        await admin.execute(f"DROP DATABASE IF EXISTS {ident(database)}")
        for role in runtime_roles:
            await admin.execute(f"DROP ROLE IF EXISTS {ident(role)}")
        await admin.execute(f"DROP ROLE IF EXISTS {ident(username)}")
    finally:
        await admin.close()
