import asyncio

import asyncpg

from app.config import settings
from app.lab import teardown_lab
from app.scenario_engine import evaluate_scenario, provision_scenario


def test_logical_backup_can_restore_only_missing_rows():
    asyncio.run(_exercise_logical_restore_lab())


async def _exercise_logical_restore_lab():
    creds = await provision_scenario("logical-backup-restore", "ci009")

    try:
        before = await evaluate_scenario("logical-backup-restore", creds.database)
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
            missing = await learner.fetchval(
                "SELECT count(*) FROM customer_accounts_backup b "
                "WHERE NOT EXISTS (SELECT 1 FROM customer_accounts a WHERE a.id = b.id)"
            )
            assert missing == 250

            await learner.execute(
                "INSERT INTO customer_accounts(id, customer_name, balance_cents, status) "
                "SELECT b.id, b.customer_name, b.balance_cents, b.status "
                "FROM customer_accounts_backup b "
                "WHERE NOT EXISTS (SELECT 1 FROM customer_accounts a WHERE a.id = b.id)"
            )
        finally:
            await learner.close()

        after = await evaluate_scenario("logical-backup-restore", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
