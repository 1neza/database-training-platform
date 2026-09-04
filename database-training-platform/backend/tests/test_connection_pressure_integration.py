import asyncio

import asyncpg

from app.config import settings
from app.evaluator import evaluate_connection_pressure
from app.lab import provision_connection_pressure, teardown_lab


def test_connection_pressure_lab_can_be_diagnosed_and_recovered():
    asyncio.run(_exercise_connection_pressure_lab())


async def _exercise_connection_pressure_lab():
    creds = await provision_connection_pressure("ci003")

    try:
        before = await evaluate_connection_pressure(creds.database)
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

            # Keep exactly the expected healthy pool size and terminate only
            # the excess application sessions.
            for row in pool_pids[3:]:
                terminated = await learner.fetchval(
                    "SELECT pg_terminate_backend($1)", row["pid"]
                )
                assert terminated is True
        finally:
            await learner.close()

        await asyncio.sleep(0.2)

        after = await evaluate_connection_pressure(creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
