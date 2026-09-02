# Scenario Authoring Specification

A scenario should define:

```json
{
  "slug": "slow-checkout-query",
  "track": "postgresql-dba",
  "level": "intermediate",
  "duration_minutes": 45,
  "environment": {
    "engine": "postgresql",
    "version": "16",
    "dataset": "ecommerce-medium"
  },
  "incident": {
    "channel": "manager",
    "message": "Checkout latency has increased..."
  },
  "faults": [
    {
      "type": "missing_index",
      "table": "orders"
    }
  ],
  "objectives": [
    "diagnose",
    "fix",
    "verify"
  ],
  "evaluation": [
    {
      "type": "index_prefix",
      "table": "orders",
      "columns": ["customer_id", "created_at"],
      "points": 50
    },
    {
      "type": "query_plan_uses_index",
      "query_id": "checkout_lookup",
      "points": 40
    }
  ]
}
```

The long-term engine should load specs like this instead of hard-coding each scenario in Python.
