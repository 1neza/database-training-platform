import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_failed_migration_can_be_completed_safely():
    asyncio.run(_exercise_failed_migration_lab())


async def _exercise_failed_migration_lab():
    creds = await provision_scenario("failed-deployment-migration", "ci007")

    try:
        before = await evaluate_scenario("failed-deployment-migration", creds.database)
        assert before["passed"] is False
        assert before["score"] == 20

        learner = await asyncpg.connect(
            host=settings.lab_admin_host,
            port=settings.lab_admin_port,
            user=creds.username,
            password=creds.password,
            database=creds.database,
        )
        try:
            remaining = await learner.fetchval(
                "SELECT count(*) FROM checkout_orders WHERE fulfillment_channel IS NULL"
            )
            assert remaining == 500

            await learner.execute(
                "UPDATE checkout_orders SET fulfillment_channel = 'manual-review' "
                "WHERE fulfillment_channel IS NULL"
            )
            await learner.execute(
                "ALTER TABLE checkout_orders ALTER COLUMN fulfillment_channel SET NOT NULL"
            )
            await learner.execute(
                "UPDATE deployment_migrations SET status = 'applied', "
                "detail = 'Backfill completed and NOT NULL constraint enforced.' "
                "WHERE migration_id = '20260904_add_fulfillment_channel'"
            )
        finally:
            await learner.close()

        after = await evaluate_scenario("failed-deployment-migration", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
