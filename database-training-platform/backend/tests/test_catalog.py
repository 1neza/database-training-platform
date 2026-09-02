from app.catalog import SCENARIOS, TRACKS


def test_default_track_exists():
    assert any(t["slug"] == "postgresql-dba" for t in TRACKS)


def test_slow_checkout_scenario_exists():
    scenario = SCENARIOS["slow-checkout-query"]
    assert scenario["duration_minutes"] == 45
    assert scenario["track_slug"] == "postgresql-dba"
