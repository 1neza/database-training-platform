import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_table_bloat_lab_can_be_vacuumed_safely():
    asyncio.run(_exercise_table_bloat_lab())


async def _exercise_table_bloat_lab():
    creds = await provision_scenario("table-bloat-vacuum", "ci008")

    try:
        before = await evaluate_scenario("table-bloat-vacuum", creds.database)
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
            live_rows = await learner.fetchval("SELECT count(*) FROM event_log")
            assert live_rows == 10000

            await learner.execute("VACUUM (ANALYZE) event_log")
        finally:
            await learner.close()

        after = await evaluate_scenario("table-bloat-vacuum", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
