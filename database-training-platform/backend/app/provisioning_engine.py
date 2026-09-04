import asyncio
import re
import secrets

import asyncpg

from .lab import (
    LabCredentials,
    admin_connect,
    create_lab_identity,
    create_login_role,
    ident,
    register_runtime_connection,
    register_runtime_role,
    role_connect,
    teardown_lab,
    terminate_connection_quietly,
)


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_SUPPORTED_FAULTS = {
    "idle_transaction_lock",
    "connection_pool",
    "concurrent_deadlock_probe",
}


class ProvisioningConfigurationError(RuntimeError):
    pass


def _safe_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_IDENTIFIER.match(value):
        raise ProvisioningConfigurationError(f"Invalid {label}: {value!r}")
    return value


def validate_provisioning_spec(spec: dict) -> None:
    if not isinstance(spec, dict):
        raise ProvisioningConfigurationError("Provisioning spec must be an object")

    setup_sql = spec.get("setup_sql")
    if not isinstance(setup_sql, list) or not setup_sql:
        raise ProvisioningConfigurationError("Provisioning spec requires setup_sql")
    if any(not isinstance(sql, str) or not sql.strip() for sql in setup_sql):
        raise ProvisioningConfigurationError("Every setup_sql entry must be non-empty SQL")

    learner = spec.get("learner", {})
    if not isinstance(learner, dict):
        raise ProvisioningConfigurationError("learner provisioning config must be an object")
    statements = learner.get("statements", [])
    if not isinstance(statements, list) or any(not isinstance(sql, str) for sql in statements):
        raise ProvisioningConfigurationError("learner.statements must be a list of SQL strings")

    aliases: set[str] = set()
    roles = spec.get("roles", [])
    if not isinstance(roles, list):
        raise ProvisioningConfigurationError("roles must be a list")
    for role in roles:
        if not isinstance(role, dict):
            raise ProvisioningConfigurationError("Each role config must be an object")
        alias = _safe_identifier(role.get("alias"), "role alias")
        _safe_identifier(role.get("prefix"), "role prefix")
        if alias in aliases:
            raise ProvisioningConfigurationError(f"Duplicate role alias: {alias}")
        aliases.add(alias)
        grants = role.get("statements", [])
        if not isinstance(grants, list) or any(not isinstance(sql, str) for sql in grants):
            raise ProvisioningConfigurationError(f"Role {alias!r} statements must be SQL strings")

    faults = spec.get("faults", [])
    if not isinstance(faults, list):
        raise ProvisioningConfigurationError("faults must be a list")
    for fault in faults:
        if not isinstance(fault, dict):
            raise ProvisioningConfigurationError("Each fault must be an object")
        fault_type = fault.get("type")
        if fault_type not in _SUPPORTED_FAULTS:
            raise ProvisioningConfigurationError(f"Unsupported fault type: {fault_type!r}")
        role_alias = fault.get("role")
        if role_alias not in aliases:
            raise ProvisioningConfigurationError(
                f"Fault {fault_type!r} references unknown role alias {role_alias!r}"
            )
        if fault_type == "connection_pool":
            count = fault.get("count")
            if not isinstance(count, int) or count <= 0:
                raise ProvisioningConfigurationError("connection_pool requires positive count")
        if fault_type == "idle_transaction_lock":
            fault_statements = fault.get("statements")
            if not isinstance(fault_statements, list) or not fault_statements:
                raise ProvisioningConfigurationError("idle_transaction_lock requires statements")
        if fault_type == "concurrent_deadlock_probe":
            fault_statements = fault.get("statements")
            if not isinstance(fault_statements, list) or len(fault_statements) != 2:
                raise ProvisioningConfigurationError(
                    "concurrent_deadlock_probe requires exactly two statements"
                )


def _render(sql: str, *, database: str, learner: str, role: str | None = None) -> str:
    values = {
        "database": ident(database),
        "learner": ident(learner),
        "role": ident(role) if role else "",
    }
    return sql.format(**values)


async def _create_runtime_roles(
    creds: LabCredentials, roles_spec: list[dict]
) -> dict[str, tuple[str, str]]:
    runtime_roles: dict[str, tuple[str, str]] = {}
    for role_spec in roles_spec:
        alias = role_spec["alias"]
        role_name = f"{role_spec['prefix']}_{creds.database.removeprefix('lab_')}"
        password = secrets.token_urlsafe(18)
        await create_login_role(role_name, password)
        register_runtime_role(creds.database, role_name)
        runtime_roles[alias] = (role_name, password)

        conn = await admin_connect(creds.database)
        try:
            for statement in role_spec.get("statements", []):
                await conn.execute(
                    _render(
                        statement,
                        database=creds.database,
                        learner=creds.username,
                        role=role_name,
                    )
                )
        finally:
            await conn.close()
    return runtime_roles


async def _inject_idle_transaction_lock(
    creds: LabCredentials, fault: dict, runtime_roles: dict[str, tuple[str, str]]
) -> None:
    role_name, password = runtime_roles[fault["role"]]
    conn = await role_connect(creds.database, role_name, password)
    try:
        application_name = fault.get("application_name")
        if application_name:
            await conn.execute("SELECT set_config('application_name', $1, false)", application_name)
        for statement in fault["statements"]:
            await conn.execute(statement)
        register_runtime_connection(creds.database, conn)
    except Exception:
        terminate_connection_quietly(conn)
        raise


async def _inject_connection_pool(
    creds: LabCredentials, fault: dict, runtime_roles: dict[str, tuple[str, str]]
) -> None:
    role_name, password = runtime_roles[fault["role"]]
    created: list[asyncpg.Connection] = []
    try:
        for _ in range(fault["count"]):
            conn = await role_connect(creds.database, role_name, password)
            application_name = fault.get("application_name")
            if application_name:
                await conn.execute("SELECT set_config('application_name', $1, false)", application_name)
            if fault.get("warmup_sql"):
                await conn.fetchval(fault["warmup_sql"])
            created.append(conn)
        for conn in created:
            register_runtime_connection(creds.database, conn)
    except Exception:
        for conn in created:
            terminate_connection_quietly(conn)
        raise


async def _inject_deadlock_probe(
    creds: LabCredentials, fault: dict, runtime_roles: dict[str, tuple[str, str]]
) -> None:
    role_name, password = runtime_roles[fault["role"]]
    connections = [
        await role_connect(creds.database, role_name, password),
        await role_connect(creds.database, role_name, password),
    ]
    deadlock_seen = False
    try:
        for index, conn in enumerate(connections, start=1):
            await conn.execute(
                "SELECT set_config('application_name', $1, false)",
                f"{fault.get('application_name', 'deadlock-worker')}-{index}",
            )

        results = await asyncio.gather(
            connections[0].execute(fault["statements"][0]),
            connections[1].execute(fault["statements"][1]),
            return_exceptions=True,
        )
        deadlock_seen = any(
            isinstance(result, asyncpg.PostgresError)
            and getattr(result, "sqlstate", None) == "40P01"
            for result in results
        )
    finally:
        for conn in connections:
            terminate_connection_quietly(conn)

    if not deadlock_seen:
        raise RuntimeError("Configured deadlock probe did not reproduce a PostgreSQL deadlock")

    event_sql = fault.get("event_sql")
    if event_sql:
        admin = await admin_connect(creds.database)
        try:
            await admin.execute(event_sql)
        finally:
            await admin.close()


async def provision_from_spec(session_short_id: str, spec: dict) -> LabCredentials:
    validate_provisioning_spec(spec)
    creds = await create_lab_identity(session_short_id)

    try:
        conn = await admin_connect(creds.database)
        try:
            for statement in spec["setup_sql"]:
                await conn.execute(statement)
            for statement in spec.get("learner", {}).get("statements", []):
                await conn.execute(
                    _render(
                        statement,
                        database=creds.database,
                        learner=creds.username,
                    )
                )
        finally:
            await conn.close()

        runtime_roles = await _create_runtime_roles(creds, spec.get("roles", []))

        for fault in spec.get("faults", []):
            if fault["type"] == "idle_transaction_lock":
                await _inject_idle_transaction_lock(creds, fault, runtime_roles)
            elif fault["type"] == "connection_pool":
                await _inject_connection_pool(creds, fault, runtime_roles)
            elif fault["type"] == "concurrent_deadlock_probe":
                await _inject_deadlock_probe(creds, fault, runtime_roles)

        return creds
    except Exception:
        await teardown_lab(creds.database, creds.username)
        raise
