"""Operator-only, source-independent public notices. Never register as an agent tool.

The operator runs dispatch_due on its own clock, regardless of agent progress.
This provides at-most-one attempt, not guaranteed delivery or timing noninterference.
"""

import re
import time
from pathlib import Path

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.models import PostArgs, ToolRequest
from zyntrava.policy import validate_destination

NOTICE = "Request accepted for protected processing."


class NoticeService:
    def __init__(self, broker: Broker, ledger: Path) -> None:
        # Separate actor/lock so model-held session state cannot choose public output.
        self.actor = Broker(broker.policy, broker.tools, broker.audit, simulated=broker.simulated)
        self.ledger = AuditStore(ledger)
        with self.ledger.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS notices "
                "(id TEXT PRIMARY KEY, destination TEXT NOT NULL, due REAL NOT NULL, "
                "policy_digest TEXT NOT NULL, state TEXT NOT NULL)"
            )

    def commit(self, agent: Broker, session: str, request_id: str, url: str, due: float) -> None:
        """Trusted operator precommit. No body, template choice or model-derived fields."""
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", request_id):
            raise ValueError("operator public request ID required")
        now = time.time()
        if not now <= due <= now + 300:
            raise ValueError("dispatch must be within the next five minutes")
        validate_destination(url)
        with agent._lock:
            state = agent._session(session)
            if state.actions or state.sensitive_read:
                raise ValueError("commit must precede all classified processing and tool actions")
            if agent.policy.digest != self.actor.policy.digest:
                raise ValueError("operator policy changed; create a new service")
            decision = self.actor.policy.evaluate(
                "post_message", PostArgs(url=url, body=NOTICE), sensitive_read=False
            )
            if decision.effect != "allow":
                raise ValueError("explicit unambiguous send permission required")
            # Unique ID is immutable even across sessions, restarts or failed delivery.
            with self.ledger.connect() as conn:
                conn.execute(
                    "INSERT INTO notices VALUES(?,?,?,?,?)",
                    (request_id, url, due, self.actor.policy.digest, "pending"),
                )
                self.actor.audit.append(
                    session_id=session,
                    phase="notice_commit",
                    tool="operator_notice",
                    status="allowed",
                    execution="not_run",
                    detected=False,
                    simulated=agent.simulated,
                    request_id=request_id,
                    template="request_accepted_v1",
                    policy_digest=self.actor.policy.digest,
                )

    def dispatch_due(self) -> list[dict[str, str]]:
        """Call from the trusted scheduler, including when the agent fails or is silent."""
        results = []
        # BEGIN IMMEDIATE serializes claimers in separate processes, not just threads.
        with self.ledger.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT id,destination,policy_digest FROM notices WHERE state='pending' "
                "AND due<=? ORDER BY due,id LIMIT 128",
                (time.time(),),
            ).fetchall()
            for request_id, _, _ in rows:
                conn.execute("UPDATE notices SET state='claimed' WHERE id=?", (request_id,))
        # Claim is durable BEFORE audit or network. Unknown delivery is never retried.
        for request_id, url, digest in rows:
            state = "failed"
            if digest == self.actor.policy.digest:
                session = self.actor.create_session()
                outcome = self.actor.submit(
                    session,
                    ToolRequest(tool="post_message", arguments={"url": url, "body": NOTICE}),
                )
                state = outcome.execution
            with self.ledger.connect() as conn:
                conn.execute("UPDATE notices SET state=? WHERE id=?", (state, request_id))
            results.append({"request_id": request_id, "execution": state})
        return results
