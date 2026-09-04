import asyncio

import asyncpg

from app.config import settings
from app.lab import provision_slow_checkout, teardown_lab
from app.scenario_engine import evaluate_scenario


def test_slow_checkout_lab_can_be_fixed_and_evaluated():
    asyncio.run(_exercise_slow_checkout_lab())


async def _exercise_slow_checkout_lab():
    creds = await provision_slow_checkout("ci001")

    try:
        before = await evaluate_scenario("slow-checkout-query", creds.database)
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
            await learner.execute(
                "CREATE INDEX idx_orders_customer_created "
                "ON orders(customer_id, created_at DESC)"
            )
            await learner.execute("ANALYZE orders")
        finally:
            await learner.close()

        after = await evaluate_scenario("slow-checkout-query", creds.database)
        assert after["passed"] is True
        assert after["score"] == 100
        assert all(check["passed"] for check in after["checks"])
    finally:
        await teardown_lab(creds.database, creds.username)
