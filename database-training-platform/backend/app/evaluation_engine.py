import asyncio
import json
import re
from typing import Any

from .lab import connect_as_admin

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_SUPPORTED_CHECKS = {
    "index_prefix",
    "query_plan_uses_index",
    "row_count",
    "session_count",
    "scalar_equals",
    "query_succeeds",
    "concurrent_sql_no_deadlock",
}
_SUPPORTED_OPERATORS = {"eq", "lte", "gte"}
_ALLOWED_SESSION_FILTERS = {"application_name", "state", "usename"}


class EvaluationConfigurationError(RuntimeError):
    pass


def _identifier(value: str) -> str:
    if not _SAFE_IDENTIFIER.match(value):
        raise EvaluationConfigurationError(f"Unsafe SQL identifier: {value!r}")
    return '"' + value + '"'


def _compare(actual: int, operator: str, expected: int) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "lte":
        return actual <= expected
    if operator == "gte":
        return actual >= expected
    raise EvaluationConfigurationError(f"Unsupported comparison operator: {operator!r}")


def _operator_label(operator: str) -> str:
    return {"eq": "=", "lte": "<=", "gte": ">="}[operator]


def _contains_index(node: dict[str, Any]) -> bool:
    if "Index" in node.get("Node Type", ""):
        return True
    return any(_contains_index(child) for child in node.get("Plans", []))


def validate_evaluation_spec(spec: dict) -> None:
    checks = spec.get("checks")
    if not isinstance(checks, list) or not checks:
        raise EvaluationConfigurationError("Evaluation spec must contain a non-empty checks list")

    total_points = 0
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise EvaluationConfigurationError(f"Evaluation check {index} must be an object")

        check_type = check.get("type")
        if check_type not in _SUPPORTED_CHECKS:
            raise EvaluationConfigurationError(f"Unsupported evaluation check type: {check_type!r}")

        name = check.get("name")
        if not isinstance(name, str) or not name.strip():
            raise EvaluationConfigurationError(f"Evaluation check {index} is missing a name")

        points = check.get("points")
        if not isinstance(points, int) or points <= 0:
            raise EvaluationConfigurationError(f"Evaluation check {name!r} needs positive integer points")
        total_points += points

        if check_type in {"row_count", "session_count"}:
            operator = check.get("operator", "eq")
            if operator not in _SUPPORTED_OPERATORS:
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} uses unsupported operator {operator!r}"
                )
            if not isinstance(check.get("expected"), int):
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} requires integer expected"
                )

        if check_type == "index_prefix":
            table = check.get("table")
            columns = check.get("columns")
            if not isinstance(table, str) or not isinstance(columns, list) or not columns:
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} requires table and columns"
                )
            _identifier(table)
            for column in columns:
                if not isinstance(column, str):
                    raise EvaluationConfigurationError(
                        f"Evaluation check {name!r} contains a non-string column"
                    )
                _identifier(column)

        if check_type == "row_count":
            table = check.get("table")
            if not isinstance(table, str):
                raise EvaluationConfigurationError(f"Evaluation check {name!r} requires table")
            _identifier(table)

        if check_type == "session_count":
            filters = check.get("filters", {})
            if not isinstance(filters, dict):
                raise EvaluationConfigurationError(f"Evaluation check {name!r} filters must be an object")
            unknown = set(filters) - _ALLOWED_SESSION_FILTERS
            if unknown:
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} uses unsupported session filters: {sorted(unknown)}"
                )

        if check_type in {"query_plan_uses_index", "scalar_equals", "query_succeeds"}:
            if not isinstance(check.get("sql"), str) or not check["sql"].strip():
                raise EvaluationConfigurationError(f"Evaluation check {name!r} requires SQL")

        if check_type == "scalar_equals" and "expected" not in check:
            raise EvaluationConfigurationError(f"Evaluation check {name!r} requires expected")

        if check_type == "concurrent_sql_no_deadlock":
            statements = check.get("statements")
            if not isinstance(statements, list) or len(statements) != 2:
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} requires exactly two concurrent statements"
                )
            if any(not isinstance(sql, str) or not sql.strip() for sql in statements):
                raise EvaluationConfigurationError(
                    f"Evaluation check {name!r} contains invalid concurrent SQL"
                )

    if total_points != 100:
        raise EvaluationConfigurationError(
            f"Evaluation checks must total 100 points; configured total is {total_points}"
        )


async def _run_concurrent_statements(database: str, statements: list[str]) -> tuple[bool, str]:
    connections = [await connect_as_admin(database), await connect_as_admin(database)]
    try:
        for conn in connections:
            await conn.execute("SET deadlock_timeout = '100ms'")

        results = await asyncio.gather(
            connections[0].execute(statements[0]),
            connections[1].execute(statements[1]),
            return_exceptions=True,
        )
        errors = [result for result in results if isinstance(result, Exception)]
        if not errors:
            return True, "both concurrent statements completed successfully"

        deadlocks = [
            error
            for error in errors
            if getattr(error, "sqlstate", None) == "40P01"
        ]
        if deadlocks:
            return False, f"PostgreSQL detected {len(deadlocks)} deadlock error(s) (SQLSTATE 40P01)"
        return False, f"concurrent execution returned {len(errors)} database error(s)"
    finally:
        for conn in connections:
            await conn.close()


async def _run_check(conn, check: dict, database: str) -> tuple[bool, str]:
    check_type = check["type"]

    if check_type == "index_prefix":
        table = check["table"]
        columns = check["columns"]
        indexes = await conn.fetch(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = $1
            """,
            table,
        )
        normalized = [row["indexdef"].lower().replace('"', '') for row in indexes]
        found = any(
            all(column.lower() in definition for column in columns)
            and all(
                definition.index(columns[i].lower()) < definition.index(columns[i + 1].lower())
                for i in range(len(columns) - 1)
            )
            for definition in normalized
        )
        return found, f"required index prefix: {', '.join(columns)}"

    if check_type == "query_plan_uses_index":
        plan_value = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {check['sql']}")
        if isinstance(plan_value, str):
            plan_value = json.loads(plan_value)
        plan = plan_value[0]["Plan"]
        found = _contains_index(plan)
        return found, f"top plan node: {plan.get('Node Type')}"

    if check_type == "row_count":
        table = _identifier(check["table"])
        actual = await conn.fetchval(f"SELECT count(*) FROM {table}")
        operator = check.get("operator", "eq")
        expected = check["expected"]
        return _compare(actual, operator, expected), (
            f"row count: {actual}; target: {_operator_label(operator)} {expected}"
        )

    if check_type == "session_count":
        filters = check.get("filters", {})
        clauses = ["datname = current_database()"]
        values: list[Any] = []
        for key, value in filters.items():
            values.append(value)
            clauses.append(f"{key} = ${len(values)}")
        sql = "SELECT count(*) FROM pg_stat_activity WHERE " + " AND ".join(clauses)
        actual = await conn.fetchval(sql, *values)
        operator = check.get("operator", "eq")
        expected = check["expected"]
        return _compare(actual, operator, expected), (
            f"matching sessions: {actual}; target: {_operator_label(operator)} {expected}"
        )

    if check_type == "scalar_equals":
        actual = await conn.fetchval(check["sql"])
        expected = check["expected"]
        return actual == expected, f"actual: {actual!r}; expected: {expected!r}"

    if check_type == "query_succeeds":
        lock_timeout_ms = int(check.get("lock_timeout_ms", 1000))
        succeeded = False
        try:
            await conn.execute(f"SET lock_timeout = '{lock_timeout_ms}ms'")
            await conn.execute(check["sql"])
            succeeded = True
        except Exception:
            succeeded = False
        finally:
            try:
                await conn.execute("SET lock_timeout = DEFAULT")
            except Exception:
                pass
        return succeeded, f"query completed within {lock_timeout_ms}ms lock timeout"

    if check_type == "concurrent_sql_no_deadlock":
        return await _run_concurrent_statements(database, check["statements"])

    raise EvaluationConfigurationError(f"Unsupported evaluation check type: {check_type!r}")


async def evaluate_checks(database: str, spec: dict) -> dict:
    validate_evaluation_spec(spec)
    conn = await connect_as_admin(database)
    checks_out: list[dict] = []
    feedback: list[str] = []
    score = 0

    try:
        for check in spec["checks"]:
            passed, detail = await _run_check(conn, check, database)
            checks_out.append({
                "name": check["name"],
                "passed": passed,
                "detail": detail,
            })
            if passed:
                score += check["points"]
            elif check.get("feedback"):
                feedback.append(check["feedback"])

        passed = all(check["passed"] for check in checks_out)
        if passed and spec.get("success_feedback"):
            feedback.append(spec["success_feedback"])

        return {
            "passed": passed,
            "score": score,
            "checks": checks_out,
            "feedback": feedback,
        }
    finally:
        await conn.close()
