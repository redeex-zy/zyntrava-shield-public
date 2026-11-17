from copy import deepcopy

import pytest

from zyntrava.lab.recovery_evidence import known_stop


def exhausted():
    return {
        "error_type": "RuntimeError",
        "api_stopped": True,
        "model_turns": 8,
        "isolation": {
            "error": "RuntimeError",
            "model_turns": 8,
            "exit_code": 1,
            "stderr": "RuntimeError: agent iteration budget exhausted\n",
            "container_absent_after_cleanup": True,
            "health": "healthy",
            "checks": {"file": True, "network": True},
        },
    }


def test_exhaustion_classifies_observation_without_mutating_error_or_result():
    row = exhausted()
    original = deepcopy(row)
    assert known_stop(row) == "model_iteration_budget_exhausted"
    assert row == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_turns", 7),
        ("stderr", "RuntimeError: unrelated failure\n"),
        ("container_absent_after_cleanup", False),
        ("health", "unhealthy"),
        ("checks", {"network": False}),
        ("exit_code", 0),
    ],
)
def test_other_errors_or_unverified_isolation_are_not_accepted(field, value):
    row = exhausted()
    row["isolation"][field] = value
    assert known_stop(row) is None


def test_management_cleanup_failure_is_not_hidden():
    row = exhausted()
    row["api_stopped"] = False
    assert known_stop(row) is None
