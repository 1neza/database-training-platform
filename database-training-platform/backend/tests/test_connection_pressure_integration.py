import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_connection_pressure_lab_can_be_diagnosed_and_recovered():
    asyncio.run(_exercise_connection_pressure_lab())


async def _exercise_connection_pressure_lab():
    creds = await provision_scenario("connection-pool-exhaustion", "ci003")

    try:
        before = await evaluate_scenario("connection-pool-exhaustion", creds.database)
        assert before["passed"] is False
        assert before["score"] < 100

        learner = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=creds.username,
            password=creds.password,
            database=creds.database,
        )
        try:
            pool_pids = await learner.fetch("""
                SELECT pid
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND application_name = 'checkout-api-pool'
                ORDER BY pid
            """)
            assert len(pool_pids) == 12

            for row in pool_pids[3:]:
                terminated = await learner.fetchval(
                    "SELECT pg_terminate_backend($1)", row["pid"]
                )
                assert terminated is True
        finally:
            await learner.close()

        await asyncio.sleep(0.2)

        after = await evaluate_scenario("connection-pool-exhaustion", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
