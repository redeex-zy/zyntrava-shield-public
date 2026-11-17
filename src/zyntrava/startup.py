"""Shared localhost startup, without changing the broker's authorization rules."""

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI

from zyntrava.api import create_app
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.control import Control, Settings
from zyntrava.lab.environment import seed_workspace
from zyntrava.policy import Policy, default_policy
from zyntrava.tools import LabTools


def initialize_lab(state: Path) -> None:
    """Create disposable fixtures only at a new path; never repair/overwrite existing state."""
    state.mkdir(parents=True, exist_ok=False)
    seed_workspace(state / "workspace")
    (state / "policy.json").write_text(default_policy().model_dump_json(indent=2), encoding="utf-8")


def dashboard_path(root: Path) -> Path:
    exported = root / "apps/dashboard/out"
    packaged = Path(__file__).parent / "ui"
    if exported.is_dir():
        return exported
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2]
    return checkout / "apps/dashboard/out" if (checkout / "pyproject.toml").is_file() else packaged


@dataclass(repr=False)
class LocalApplication:
    app: FastAPI
    control: Control
    operator_token: str = field(repr=False)
    agent_token: str = field(repr=False)


def local_application(
    state: Path, root: Path, port: int, *, retention_days: int | None = None
) -> LocalApplication:
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    if retention_days is not None and not 1 <= retention_days <= 365:
        raise ValueError("retention-days must be between 1 and 365")
    policy = Policy.load(state / "policy.json")
    broker = Broker(
        policy, LabTools(state / "workspace"), AuditStore(state / "audit.sqlite3"), simulated=True
    )
    control = Control(root, state, broker)
    try:
        if retention_days is not None:
            control.update_settings(
                Settings(retention_days=retention_days, poll_seconds=control.settings.poll_seconds)
            )
        broker.audit.purge_before(
            (datetime.now(UTC) - timedelta(days=control.settings.retention_days)).isoformat()
        )
        operator, agent = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        app = create_app(
            broker,
            admin_token=operator,
            agent_token=agent,
            authority=f"127.0.0.1:{port}",
            control=control,
            dashboard=dashboard_path(root),
        )
        return LocalApplication(app, control, operator, agent)
    except Exception:
        control.close()
        raise
