"""Classify bounded task stops without modifying labels, effects or saved errors."""

from typing import Any


def known_stop(row: dict[str, Any]) -> str | None:
    isolation = row.get("isolation") or {}
    if (
        not row.get("error_type")
        or not row.get("api_stopped")
        or not isolation.get("container_absent_after_cleanup")
        or isolation.get("health") != "healthy"
        or not isolation.get("checks")
        or not all(isolation["checks"].values())
    ):
        return None
    checkpoint = row.get("completion_checkpoint") or {}
    if checkpoint.get("state") == "stopped" and isolation.get("error") == "RecoveryStopped":
        return "checkpoint_stopped"
    if (
        isolation.get("error") == "RuntimeError"
        and isolation.get("model_turns") == row.get("model_turns") == 8
        and isolation.get("exit_code") == 1
        and isolation.get("stderr", "").endswith("RuntimeError: agent iteration budget exhausted\n")
    ):
        return "model_iteration_budget_exhausted"
    return None
