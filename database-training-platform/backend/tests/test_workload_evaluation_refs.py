import pytest

from app.evaluation_engine import EvaluationConfigurationError, validate_evaluation_spec


def _spec(sql_ref: dict) -> dict:
    return {
        "checks": [
            {
                "type": "query_plan_uses_index",
                "name": "plan",
                "sql_ref": sql_ref,
                "points": 100,
            }
        ]
    }


def test_valid_workload_sql_ref_is_accepted():
    validate_evaluation_spec(
        _spec(
            {
                "workload": "checkout-customer-history",
                "version": "1.0.0",
                "statement": "recent_orders",
            }
        )
    )


def test_unknown_workload_is_rejected():
    with pytest.raises(EvaluationConfigurationError, match="Unknown workload"):
        validate_evaluation_spec(
            _spec(
                {
                    "workload": "missing",
                    "version": "1.0.0",
                    "statement": "recent_orders",
                }
            )
        )


def test_wrong_workload_version_is_rejected():
    with pytest.raises(EvaluationConfigurationError, match="available version"):
        validate_evaluation_spec(
            _spec(
                {
                    "workload": "checkout-customer-history",
                    "version": "9.9.9",
                    "statement": "recent_orders",
                }
            )
        )


def test_missing_workload_statement_is_rejected():
    with pytest.raises(EvaluationConfigurationError, match="has no statement"):
        validate_evaluation_spec(
            _spec(
                {
                    "workload": "checkout-customer-history",
                    "version": "1.0.0",
                    "statement": "missing",
                }
            )
        )
