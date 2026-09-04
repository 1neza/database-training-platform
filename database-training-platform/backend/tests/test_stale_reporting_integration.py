import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_stale_reporting_transaction_can_be_cleared():
    asyncio.run(_exercise_stale_reporting_transaction())


async def _exercise_stale_reporting_transaction():
    creds = await provision_scenario("stale-reporting-transaction", "ci005")

    try:
        before = await evaluate_scenario("stale-reporting-transaction", creds.database)
        assert before["passed"] is False
        assert before["score"] == 40

        learner = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=creds.username,
            password=creds.password,
            database=creds.database,
        )
        try:
            reporter_pid = await learner.fetchval("""
                SELECT pid
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND application_name = 'weekly-report-worker'
                  AND state = 'idle in transaction'
                LIMIT 1
            """)
            assert reporter_pid is not None
            terminated = await learner.fetchval(
                "SELECT pg_terminate_backend($1)", reporter_pid
            )
            assert terminated is True
        finally:
            await learner.close()

        await asyncio.sleep(0.2)

        after = await evaluate_scenario("stale-reporting-transaction", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
