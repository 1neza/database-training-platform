import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_deadlock_lab_can_be_reproduced_fixed_and_evaluated():
    asyncio.run(_exercise_deadlock_lab())


async def _exercise_deadlock_lab():
    creds = await provision_scenario("deadlock-transfer-procedures", "ci004")

    try:
        admin = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=settings.lab_admin_user,
            password=settings.lab_admin_password,
            database=creds.database,
        )
        try:
            incident_count = await admin.fetchval(
                "SELECT count(*) FROM incident_events WHERE event_type = 'deadlock'"
            )
            assert incident_count == 1
        finally:
            await admin.close()

        before = await evaluate_scenario("deadlock-transfer-procedures", creds.database)
        assert before["passed"] is False
        assert before["score"] == 35
        assert before["checks"][0]["passed"] is False

        learner = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=creds.username,
            password=creds.password,
            database=creds.database,
        )
        try:
            await learner.execute("""
                CREATE OR REPLACE FUNCTION transfer_reverse() RETURNS void
                LANGUAGE plpgsql SECURITY DEFINER AS $$
                BEGIN
                    PERFORM 1 FROM transfer_accounts WHERE id = 1 FOR UPDATE;
                    PERFORM pg_sleep(0.25);
                    PERFORM 1 FROM transfer_accounts WHERE id = 2 FOR UPDATE;
                    UPDATE transfer_accounts SET balance_cents = balance_cents - 100 WHERE id = 2;
                    UPDATE transfer_accounts SET balance_cents = balance_cents + 100 WHERE id = 1;
                END;
                $$;
            """)
        finally:
            await learner.close()

        after = await evaluate_scenario("deadlock-transfer-procedures", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
