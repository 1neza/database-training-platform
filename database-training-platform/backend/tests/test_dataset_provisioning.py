import pytest

from app.provisioning_engine import ProvisioningConfigurationError, validate_provisioning_spec


def _base_spec(dataset_ref: dict) -> dict:
    return {
        "datasets": [dataset_ref],
        "setup_sql": [],
        "roles": [],
        "faults": [],
    }


def test_unknown_dataset_reference_is_rejected():
    with pytest.raises(ProvisioningConfigurationError, match="Unknown dataset"):
        validate_provisioning_spec(
            _base_spec({"slug": "does-not-exist", "version": "1.0.0"})
        )


def test_dataset_version_mismatch_is_rejected():
    with pytest.raises(ProvisioningConfigurationError, match="available version"):
        validate_provisioning_spec(
            _base_spec({"slug": "ecommerce-orders-medium", "version": "9.9.9"})
        )


def test_dataset_can_satisfy_setup_requirement_without_inline_sql():
    validate_provisioning_spec(
        _base_spec({"slug": "ecommerce-orders-medium", "version": "1.0.0"})
    )
