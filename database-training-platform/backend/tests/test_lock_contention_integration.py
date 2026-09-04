import asyncio

import asyncpg

from app.config import settings
from app.evaluator import evaluate_blocked_payment
from app.lab import provision_blocked_payment, teardown_lab


def test_blocked_payment_lab_can_be_diagnosed_and_recovered():
    asyncio.run(_exercise_blocked_payment_lab())


async def _exercise_blocked_payment_lab():
    creds = await provision_blocked_payment("ci002")

    try:
        before = await evaluate_blocked_payment(creds.database)
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
            blocker_pid = await learner.fetchval("""
                SELECT pid
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND application_name = 'legacy-payment-worker'
                  AND state = 'idle in transaction'
                LIMIT 1
            """)
            assert blocker_pid is not None
            terminated = await learner.fetchval("SELECT pg_terminate_backend($1)", blocker_pid)
            assert terminated is True
        finally:
            await learner.close()

        # Give PostgreSQL a brief moment to clear the terminated backend state.
        await asyncio.sleep(0.2)

        after = await evaluate_blocked_payment(creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
