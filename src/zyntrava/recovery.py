"""Operator-authorized, single-effect task state machine. Not a general planner.

Only this controller's bound submit method is exposed by the supported task bridge.
The broker/ledger/verifier/operator remain trusted. Never register operator methods
as model tools or resume classified history in a fresh session after restart.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import Field, model_validator

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.json_input import strict_json
from zyntrava.models import Outcome, PostArgs, ReadArgs, StrictModel, ToolRequest
from zyntrava.paths import path_parts
from zyntrava.policy import validate_destination

Receipt = Literal["verified", "absent", "conflict", "unavailable"]
ACTIVE = {"ready", "read"}


def canonical_body(value: str) -> str:
    parsed = strict_json(value)
    if not isinstance(parsed, dict):
        raise ValueError("exact JSON object required")
    return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class TaskPlan(StrictModel):
    task_id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    authorization_id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    session_id: str = Field(min_length=1, max_length=64)
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: ReadArgs
    payment: PostArgs
    expires_at: float = Field(allow_inf_nan=False)
    max_actions: int = Field(default=12, ge=2, le=32)
    max_recoveries: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def exact_scope(self) -> "TaskPlan":
        path_parts(self.source.path)
        validate_destination(self.payment.url)
        canonical_body(self.payment.body)
        return self


class ReceiptVerifier(Protocol):
    def __call__(self, authorization_id: str, payment: PostArgs, /) -> Receipt: ...


class TaskController:
    def __init__(
        self, broker: Broker, ledger: Path, verifier: ReceiptVerifier | None = None
    ) -> None:
        if broker.mode != "full":
            raise ValueError("task recovery requires full broker enforcement")
        if ledger.resolve() == broker.audit.path.resolve():
            raise ValueError("task ledger must be separate from the audit database")
        self.broker, self.verifier = broker, verifier
        self.ledger = AuditStore(ledger)
        with self.ledger.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, "
                "authorization TEXT UNIQUE NOT NULL, plan TEXT NOT NULL, state TEXT NOT NULL, "
                "read_done INTEGER NOT NULL DEFAULT 0, claimed INTEGER NOT NULL DEFAULT 0, "
                "actions INTEGER NOT NULL DEFAULT 0, denials INTEGER NOT NULL DEFAULT 0, "
                "recoveries INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL, "
                "updated REAL NOT NULL)"
            )

    def _event(self, task_id: str, state: str, reason: str) -> str:
        # No objective prose, source contents, account fields or model error strings.
        return self.broker.audit.append(
            task_id=task_id,
            phase="decision" if state == "blocked" else "recovery",
            tool="task_controller",
            status=state,
            reason=reason,
            execution="not_run",
            detected=False,
            simulated=self.broker.simulated,
            decision=self.broker.policy.deny(
                "task_authorization",
                reason,
                "The proposed action exceeds the current trusted task scope.",
            ).model_dump()
            if state == "blocked"
            else None,
        )

    def register(self, plan: TaskPlan) -> None:
        """Operator only. The immutable authorization is never derived from a document."""
        with self.broker._lock:
            session = self.broker._session(plan.session_id)
            if session.actions or session.sensitive_read:
                raise ValueError("register before agent processing")
            if plan.policy_digest != self.broker.policy.digest or plan.expires_at <= time.time():
                raise ValueError("stale authorization")
            if plan.expires_at > time.time() + 3600:
                raise ValueError("authorization lifetime exceeds one hour")
            with self.ledger.connect() as conn:
                conn.execute(
                    "INSERT INTO tasks(id,authorization,plan,state,reason,updated) "
                    "VALUES(?,?,?,'ready','operator_authorized',?)",
                    (plan.task_id, plan.authorization_id, plan.model_dump_json(), time.time()),
                )
                self._event(plan.task_id, "ready", "operator_authorized")

    @staticmethod
    def _row(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("unknown task")
        return dict(row)

    def _set(self, conn: sqlite3.Connection, task_id: str, state: str, reason: str) -> None:
        self._event(task_id, state, reason)  # Fail closed before reporting progress.
        conn.execute(
            "UPDATE tasks SET state=?,reason=?,updated=? WHERE id=?",
            (state, reason, time.time(), task_id),
        )

    def _denied(self, task_id: str, reason: str) -> Outcome:
        decision = self.broker.policy.deny(
            "task_authorization",
            reason,
            "Task continuation is outside its current operator authorization or execution state.",
        )
        event = self._event(task_id, "blocked", reason)
        return Outcome(event_id=event, status="blocked", execution="not_run", decision=decision)

    def _authority(self, plan: TaskPlan, session: str) -> str | None:
        if session != plan.session_id:
            return "session_not_bound"
        try:
            self.broker._session(session)
        except ValueError:
            return "session_unavailable"
        if plan.policy_digest != self.broker.policy.digest:
            return "policy_revoked"
        if plan.expires_at <= time.time():
            return "authorization_expired"
        return None

    def submit(self, task_id: str, session: str, request: ToolRequest) -> Outcome:
        request = ToolRequest.model_validate_json(request.model_dump_json())
        with self.broker._lock:
            with self.ledger.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = self._row(conn, task_id)
                plan = TaskPlan.model_validate_json(row["plan"])
                invalid = self._authority(plan, session)
                if invalid:
                    # A foreign session must not cancel or mutate somebody else's task.
                    if invalid != "session_not_bound" and row["state"] in ACTIVE:
                        self._set(conn, task_id, "stopped", invalid)
                    return self._denied(task_id, invalid)
                if row["state"] not in ACTIVE:
                    return self._denied(task_id, "task_not_active")
                conn.execute("UPDATE tasks SET actions=actions+1 WHERE id=?", (task_id,))
                if row["actions"] >= plan.max_actions:
                    self._set(conn, task_id, "stopped", "action_budget_exhausted")
                    return self._denied(task_id, "action_budget_exhausted")
                is_read = request.tool == "read_file" and request.arguments == {
                    "path": plan.source.path
                }
                is_pay = False
                try:
                    is_pay = (
                        request.tool == "post_message"
                        and set(request.arguments) == {"url", "body"}
                        and request.arguments["url"] == plan.payment.url
                        and isinstance(request.arguments["body"], str)
                        and canonical_body(request.arguments["body"])
                        == canonical_body(plan.payment.body)
                    )
                except ValueError:
                    pass
                if (
                    not (is_read or is_pay)
                    or (is_read and row["read_done"])
                    or (is_pay and not row["read_done"])
                ):
                    conn.execute("UPDATE tasks SET denials=denials+1 WHERE id=?", (task_id,))
                    return self._denied(task_id, "exact_task_scope")
                if is_pay and row["claimed"]:
                    return self._denied(task_id, "payment_already_claimed")
                # This claim is durable BEFORE broker audit/transport. Never replay a payment.
                conn.execute(
                    "UPDATE tasks SET state=?,claimed=?,updated=? WHERE id=?",
                    ("claimed" if is_pay else "reading", int(is_pay), time.time(), task_id),
                )
            outcome = self.broker.submit(session, request)
            if is_read:
                with self.ledger.connect() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    current = self._row(conn, task_id)
                    if current["state"] == "reading":
                        success = outcome.execution == "succeeded"
                        self._set(
                            conn,
                            task_id,
                            "read" if success else "stopped",
                            "source_read" if success else "source_unavailable",
                        )
                        conn.execute(
                            "UPDATE tasks SET read_done=? WHERE id=?", (int(success), task_id)
                        )
            else:
                if outcome.execution == "not_run":
                    with self.ledger.connect() as conn:
                        self._set(conn, task_id, "stopped", "broker_refused_payment")
                else:
                    self.reconcile(task_id)
            return outcome

    def reconcile(self, task_id: str) -> str:
        """Read-only receipt/state reconciliation; never reissues a payment."""
        with self.ledger.connect() as conn:
            row = self._row(conn, task_id)
        if row["state"] == "verified" or not row["claimed"]:
            return str(row["state"])
        plan = TaskPlan.model_validate_json(row["plan"])
        receipt: Receipt = "unavailable"
        if self.verifier is not None:
            try:
                receipt = self.verifier(plan.authorization_id, plan.payment)
            except Exception:
                receipt = "unavailable"  # No raw errors or model-certified success.
        state = "verified" if receipt == "verified" else "uncertain"
        with self.ledger.connect() as conn:
            self._set(
                conn,
                task_id,
                state,
                "receipt_verified" if state == "verified" else "operator_reconciliation_required",
            )
        return state

    def cancel(self, task_id: str) -> bool:
        """Operator only. False means dispatch already claimed/finished, not reversed."""
        with self.ledger.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = self._row(conn, task_id)
            if row["claimed"] or row["state"] == "verified":
                return False
            self._set(conn, task_id, "cancelled", "operator_cancelled")
            return True

    def recover(self, task_id: str, *, require_denial: bool = True) -> dict[str, Any]:
        """Operator/controller only. Resume a typed plan, never run a second agent."""
        with self.broker._lock:
            with self.ledger.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = self._row(conn, task_id)
                plan = TaskPlan.model_validate_json(row["plan"])
                if row["state"] not in ACTIVE or (require_denial and not row["denials"]):
                    return self.status(task_id)
                invalid = self._authority(plan, plan.session_id)
                stop = bool(invalid or row["recoveries"] >= plan.max_recoveries)
                if stop:
                    self._set(conn, task_id, "stopped", invalid or "recovery_budget_exhausted")
                else:
                    self._event(task_id, "continuation_approved", "trusted_plan_revalidated")
                    conn.execute("UPDATE tasks SET recoveries=recoveries+1 WHERE id=?", (task_id,))
            if stop:
                return self.status(task_id)
            if not row["read_done"]:
                result = self.submit(
                    task_id,
                    plan.session_id,
                    ToolRequest(tool="read_file", arguments={"path": plan.source.path}),
                )
                if result.execution != "succeeded":
                    return self.status(task_id)
            self.submit(
                task_id,
                plan.session_id,
                ToolRequest(tool="post_message", arguments=plan.payment.model_dump()),
            )
            return self.status(task_id)

    def status(self, task_id: str) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            row = self._row(conn, task_id)
        return {
            key: row[key]
            for key in (
                "id",
                "state",
                "read_done",
                "claimed",
                "actions",
                "denials",
                "recoveries",
                "reason",
                "updated",
            )
        }


def task_statuses(ledger: Path) -> list[dict[str, Any]]:
    """Operator-only redacted view. Never exports plans or model/source content."""
    if not ledger.is_file():
        return []
    with sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        # A job may have created its ledger file but not committed the schema yet.
        if (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
            ).fetchone()
            is None
        ):
            return []
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id,state,read_done,claimed,actions,denials,recoveries,reason,updated "
                "FROM tasks ORDER BY updated DESC LIMIT 100"
            )
        ]
