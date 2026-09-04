from .catalog import SCENARIOS, SCENARIO_DIRECTORY
from .scenario_engine import validate_scenario_catalog


def main() -> None:
    validate_scenario_catalog()
    print(
        f"Validated {len(SCENARIOS)} scenario file(s) in {SCENARIO_DIRECTORY}"
    )


if __name__ == "__main__":
    main()
