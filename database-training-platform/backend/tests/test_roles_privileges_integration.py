import asyncio
import re

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


_ROLE_NAME = re.compile(r"^analytics_export_[a-zA-Z0-9_]+$")


def test_excessive_analytics_privileges_can_be_remediated():
    asyncio.run(_exercise_roles_privileges_lab())


async def _exercise_roles_privileges_lab():
    creds = await provision_scenario("excessive-analytics-privileges", "ci006")

    try:
        before = await evaluate_scenario("excessive-analytics-privileges", creds.database)
        assert before["passed"] is False
        assert before["score"] == 50

        learner = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=creds.username,
            password=creds.password,
            database=creds.database,
        )
        try:
            role_name = await learner.fetchval(
                """
                SELECT grantee
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public'
                  AND table_name = 'customer_exports'
                  AND grantee LIKE 'analytics_export_%'
                ORDER BY grantee
                LIMIT 1
                """
            )
            assert role_name is not None
            assert _ROLE_NAME.fullmatch(role_name)

            quoted_role = '"' + role_name.replace('"', '""') + '"'
            await learner.execute(
                f"REVOKE INSERT, UPDATE, DELETE ON customer_exports FROM {quoted_role}"
            )

            can_select = await learner.fetchval(
                "SELECT has_table_privilege($1, 'customer_exports', 'SELECT')",
                role_name,
            )
            can_update = await learner.fetchval(
                "SELECT has_table_privilege($1, 'customer_exports', 'UPDATE')",
                role_name,
            )
            assert can_select is True
            assert can_update is False
        finally:
            await learner.close()

        after = await evaluate_scenario("excessive-analytics-privileges", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
