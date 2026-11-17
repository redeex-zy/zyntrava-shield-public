"""Trusted reference monitor for supported tool dispatch. All I/O passes here."""

import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from zyntrava.audit import AuditStore
from zyntrava.detection import instructions_in, secrets_in
from zyntrava.models import CountArgs, Decision, Outcome, ReadArgs, ToolRequest
from zyntrava.paths import within
from zyntrava.policy import Policy
from zyntrava.tools import ACTION_ERRORS, LabTools, parse_action


@dataclass
class Session:
    sensitive_read: bool = False
    actions: int = 0


@dataclass(frozen=True)
class Pending:
    session_id: str
    request_json: str  # Exact immutable snapshot, memory only.
    policy_digest: str
    expires: float


@dataclass
class Broker:
    policy: Policy
    tools: LabTools
    audit: AuditStore
    mode: Literal["full", "basic"] = "full"
    simulated: bool = (
        False  # True for synthetic research/demo traffic, with real local side effects.
    )
    approval_ttl: int = 300
    _sessions: dict[str, Session] = field(default_factory=dict, init=False, repr=False)
    _pending: dict[str, Pending] = field(default_factory=dict, init=False, repr=False)
    _release_counts: dict[tuple[str, str], int] = field(
        default_factory=dict, init=False, repr=False
    )
    _lock: Any = field(default_factory=threading.RLock, init=False, repr=False)
    _audit_key: bytes = field(
        default_factory=lambda: secrets.token_bytes(32), init=False, repr=False
    )

    def create_session(self) -> str:
        with self._lock:
            if len(self._sessions) >= 1000:
                raise ValueError("session capacity reached; restart the local broker")
            session_id = str(uuid4())
            self._sessions[session_id] = Session()
            return session_id

    def _session(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise ValueError("unknown or expired session") from None

    def observe(self, session_id: str, text: str, source: Literal["user", "tool"]) -> None:
        with self._lock:
            if len(text) > 32768:
                raise ValueError("source exceeds the 32 Ki-character limit")
            session = self._session(session_id)
            evidence = instructions_in(text, source)
            sensitive = secrets_in(text)
            # A secret in a user prompt is also a sensitive source in full mode.
            if sensitive:
                session.sensitive_read = True
            if evidence or sensitive:
                self.audit.append(
                    session_id=session_id,
                    phase="observation",
                    tool=None,
                    status="detected",
                    execution="not_run",
                    detected=True,
                    simulated=self.simulated,
                    source=source,
                    evidence=[e.model_dump() for e in (*evidence, *sensitive)],
                )

    def _record(
        self,
        session_id: str,
        request: ToolRequest,
        decision: Decision,
        status: str,
        execution: str,
        phase: str = "decision",
    ) -> str:
        # Keyed digest avoids storing arguments or a dictionary-testable raw secret hash.
        fingerprint = hmac.new(
            self._audit_key, request.model_dump_json().encode(), hashlib.sha256
        ).hexdigest()
        tool = (
            request.tool
            if request.tool
            in {
                "read_file",
                "write_file",
                "post_message",
                "fetch_page",
                "export_count",
                "final_answer",
            }
            else "unknown"
        )
        return self.audit.append(
            session_id=session_id,
            tool=tool,
            phase=phase,
            status=status,
            execution=execution,
            detected=bool(decision.evidence),
            simulated=self.simulated,
            action_fingerprint=fingerprint,
            decision=decision.model_dump(),
        )

    def submit(self, session_id: str, request: ToolRequest) -> Outcome:
        with self._lock:
            snapshot = request.model_dump_json()
            return self._submit(session_id, ToolRequest.model_validate_json(snapshot))

    def _submit(self, session_id: str, request: ToolRequest, *, approved: bool = False) -> Outcome:
        session = self._session(session_id)
        session.actions += 1
        try:
            tool, args = parse_action(request)
            self.tools.validate(args)
            decision = self.policy.evaluate(
                tool, args, sensitive_read=session.sensitive_read, full=self.mode == "full"
            )
        except ACTION_ERRORS:
            decision = self.policy.deny(
                "invalid_tool_call",
                "closed_tool_schema",
                "Unsupported tool, invalid arguments or unsafe resource.",
            )
        if session.actions > 1000:
            decision = self.policy.deny(
                "unexpected_action_sequence",
                "session_action_budget",
                "Session action budget exceeded; execution stopped.",
            )
        if decision.effect == "allow" and request.tool == "export_count":
            release = CountArgs.model_validate(request.arguments)
            used = self._release_counts.get((release.path, release.url), 0)
            if used >= self.policy.release_budget(release):
                decision = self.policy.deny(
                    "release_budget_exhausted",
                    "release_budget",
                    "Operator release budget exhausted for this broker lifetime and scope.",
                )
        status: Literal["allowed", "blocked", "sent_for_approval"] = (
            "blocked"
            if decision.effect == "deny"
            else "sent_for_approval"
            if decision.effect == "approve" and not approved
            else "allowed"
        )
        event_id = self._record(session_id, request, decision, status, "not_run")
        if status == "blocked":
            return Outcome(event_id=event_id, status=status, execution="not_run", decision=decision)
        if status == "sent_for_approval":
            self._expire_pending()
            if len(self._pending) >= 1000:
                raise ValueError("approval capacity reached")
            approval_id = str(uuid4())
            self._pending[approval_id] = Pending(
                session_id,
                request.model_dump_json(),
                self.policy.digest,
                time.monotonic() + self.approval_ttl,
            )
            return Outcome(
                event_id=event_id,
                status=status,
                execution="not_run",
                decision=decision,
                approval_id=approval_id,
            )
        # The durable authorization record must succeed before any side effect.
        # Failed post-effect logging leaves a pre-execution record with unknown completion.
        try:
            tool, args = parse_action(request)
            if tool == "export_count" and isinstance(args, CountArgs):
                session.sensitive_read = True  # Release never clears session confidentiality.
                # Consume before source access, including invalid documents/uncertain I/O.
                scope = (args.path, args.url)
                self._release_counts[scope] = self._release_counts.get(scope, 0) + 1
                output = self.tools.execute(tool, args, count_limit=self.policy.count_limit(args))
            else:
                output = self.tools.execute(tool, args)
            if tool == "read_file" and isinstance(args, ReadArgs):
                if any(within(root, args.path) for root in self.policy.sensitive_roots):
                    session.sensitive_read = True
            self.observe(session_id, output, "tool")
            execution: Literal["succeeded", "failed"] = "succeeded"
        except ACTION_ERRORS:
            output = None  # Do not expose exception paths, server bodies or secret values.
            execution = "failed"
        try:
            event_id = self._record(session_id, request, decision, status, execution, "execution")
        except (OSError, sqlite3.Error):
            # An effect may already have occurred. Never mislabel it blocked or safe to retry.
            return Outcome(event_id=event_id, status=status, execution="unknown", decision=decision)
        return Outcome(
            event_id=event_id, status=status, execution=execution, decision=decision, output=output
        )

    def final_answer(self, session_id: str, text: str) -> Outcome:
        """Mediate the supported adapter's non-streamed return to its caller.

        This cannot retract data already delivered to the inference provider or
        constrain direct calls, callbacks, hostile plugins, or saved transcripts.
        """
        with self._lock:
            session = self._session(session_id)
            forbidden = (
                len(text) > 16384
                or bool(secrets_in(text))
                or (self.mode == "full" and session.sensitive_read)
            )
            decision = (
                self.policy.deny(
                    "sensitive_answer_withheld",
                    "final_answer_boundary",
                    "Final answer exceeds output scope or follows a classified source.",
                )
                if forbidden
                else Decision(effect="allow", policy_digest=self.policy.digest)
            )
            # Audit a keyed fingerprint of a fixed omission, never raw answer content.
            # Oversized answers are also omitted so logging cannot exceed input bounds.
            request = ToolRequest(tool="final_answer", arguments={"content": "omitted"})
            status: Literal["allowed", "blocked"] = "blocked" if forbidden else "allowed"
            event_id = self._record(
                session_id, request, decision, status, "not_run", "answer_decision"
            )
            # Failure here raises before any value can be returned to the caller.
            if not forbidden:
                event_id = self._record(
                    session_id, request, decision, status, "succeeded", "answer_release"
                )
            return Outcome(
                event_id=event_id,
                status=status,
                execution="not_run" if forbidden else "succeeded",
                decision=decision,
                output=None if forbidden else text,
            )

    def _expire_pending(self) -> None:
        now = time.monotonic()
        for key in tuple(self._pending):
            if self._pending[key].expires <= now:
                del self._pending[key]

    def approvals(self) -> list[dict[str, Any]]:
        with self._lock:
            self._expire_pending()
            result = []
            for key, pending in self._pending.items():
                request = ToolRequest.model_validate_json(pending.request_json)
                # Operator preview is ephemeral and requires the admin credential.
                # Sink bodies containing recognizable secrets never reach approval.
                result.append(
                    {
                        "id": key,
                        "session_id": pending.session_id,
                        "action": request.model_dump(),
                        "policy_digest": pending.policy_digest,
                        "expires_in_seconds": max(0, int(pending.expires - time.monotonic())),
                    }
                )
            return result

    def resolve(self, approval_id: str, allow: bool) -> Outcome:
        # This method is operator-only. It is never registered with the agent.
        with self._lock:
            pending = self._pending.pop(approval_id, None)
            if pending is None:
                raise ValueError("unknown or already consumed approval")
            request = ToolRequest.model_validate_json(pending.request_json)
            if (
                not allow
                or pending.expires <= time.monotonic()
                or pending.policy_digest != self.policy.digest
            ):
                decision = self.policy.deny(
                    "approval_rejected",
                    "approval_invalid",
                    "Approval was rejected, expired or bound to an old policy.",
                )
                event_id = self._record(
                    pending.session_id, request, decision, "blocked", "not_run", "approval"
                )
                return Outcome(
                    event_id=event_id, status="blocked", execution="not_run", decision=decision
                )
            self.audit.append(
                session_id=pending.session_id,
                phase="approval",
                tool=request.tool,
                status="approved",
                execution="not_run",
                simulated=self.simulated,
                detected=False,
                approval_id=approval_id,
            )
            # Latest session labels and policy still apply. Approval never overrides a deny.
            return self._submit(pending.session_id, request, approved=True)

    def overview(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self.audit.stats(),
                "pending_approvals": len(self.approvals()),
                "active_sessions": len(self._sessions),
                "mode": self.mode,
                "integration_status": "framework-fixture-tests-only",
            }
