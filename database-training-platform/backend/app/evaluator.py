from .lab import connect_as_admin


async def evaluate_slow_checkout(database: str) -> dict:
    conn = await connect_as_admin(database)
    checks = []
    feedback = []
    score = 0

    try:
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'orders'
        """)

        defs = [row["indexdef"].lower().replace('"', '') for row in indexes]
        composite_ok = any(
            "customer_id" in d
            and "created_at" in d
            and d.index("customer_id") < d.index("created_at")
            for d in defs
        )

        checks.append({
            "name": "Composite index exists",
            "passed": composite_ok,
            "detail": "Expected an orders index beginning with customer_id and including created_at.",
        })
        if composite_ok:
            score += 50
        else:
            feedback.append(
                "Create an index whose leading columns match the filter and ordering pattern, "
                "for example customer_id followed by created_at."
            )

        plan_rows = await conn.fetch("""
            EXPLAIN (FORMAT JSON)
            SELECT id, status, total_cents, created_at
            FROM orders
            WHERE customer_id = 4242
            ORDER BY created_at DESC
            LIMIT 20
        """)
        plan = plan_rows[0][0][0]["Plan"]

        def contains_index(node):
            if "Index" in node.get("Node Type", ""):
                return True
            return any(contains_index(child) for child in node.get("Plans", []))

        indexed_plan = contains_index(plan)
        checks.append({
            "name": "Challenge query uses an index",
            "passed": indexed_plan,
            "detail": f"Top plan node: {plan.get('Node Type')}",
        })
        if indexed_plan:
            score += 40
        else:
            feedback.append("The checkout query is still not receiving an indexed plan.")

        order_count = await conn.fetchval("SELECT count(*) FROM orders")
        data_preserved = order_count >= 350000
        checks.append({
            "name": "Production data preserved",
            "passed": data_preserved,
            "detail": f"orders row count: {order_count}",
        })
        if data_preserved:
            score += 10
        else:
            feedback.append("The task must be solved without deleting the production dataset.")

        passed = composite_ok and indexed_plan and data_preserved
        if passed:
            feedback.append(
                "The environment now has an index aligned with the production lookup pattern, "
                "and PostgreSQL can use it for the challenge query."
            )

        return {
            "passed": passed,
            "score": score,
            "checks": checks,
            "feedback": feedback,
        }
    finally:
        await conn.close()
