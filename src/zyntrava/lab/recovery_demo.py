"""Operator-triggered synthetic recovery demo. No model or actual financial service."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.lab.receipts import PaymentTools, ReceiptBank
from zyntrava.models import PostArgs, ReadArgs, ToolRequest
from zyntrava.policy import Policy, Rule
from zyntrava.recovery import TaskController, TaskPlan


def run_demo(state: Path, audit: AuditStore) -> dict[str, Any]:
    identity = "demo-" + str(uuid4())
    with tempfile.TemporaryDirectory(prefix="zyntrava-recovery-demo-") as directory:
        base = Path(directory)
        (base / "public").mkdir()
        (base / "public/bill.txt").write_text("Synthetic public invoice.", encoding="utf-8")
        bank = ReceiptBank(base / "bank.db", {"transactions": []})
        with bank.serve() as url:
            policy = Policy(
                version=1,
                name="recovery-demo",
                rules=(
                    Rule(id="invoice", tool="read_file", effect="allow", path_prefix="public"),
                    Rule(
                        id="payment",
                        tool="post_message",
                        effect="allow",
                        destination=url,
                        body_fields=(("recipient", "owned-simulator"), ("amount", 98.7)),
                    ),
                ),
            )
            broker = Broker(policy, PaymentTools(base, identity, url), audit, simulated=True)
            session = broker.create_session()
            controller = TaskController(broker, state / "tasks.sqlite3", bank.verify)
            plan = TaskPlan(
                task_id=identity,
                authorization_id=identity,
                session_id=session,
                policy_digest=policy.digest,
                source=ReadArgs(path="public/bill.txt"),
                payment=PostArgs(
                    url=url, body=json.dumps({"recipient": "owned-simulator", "amount": 98.7})
                ),
                expires_at=time.time() + 300,
            )
            controller.register(plan)
            controller.submit(
                identity, session, ToolRequest(tool="read_file", arguments=plan.source.model_dump())
            )
            controller.submit(
                identity,
                session,
                ToolRequest(
                    tool="post_message",
                    arguments={
                        "url": url,
                        "body": json.dumps({"recipient": "not-authorized", "amount": 1000.0}),
                    },
                ),
            )
            result = controller.recover(identity)
            duplicate = controller.submit(
                identity,
                session,
                ToolRequest(tool="post_message", arguments=plan.payment.model_dump()),
            )
            if result["state"] != "verified" or bank.posts != 1 or duplicate.status != "blocked":
                raise RuntimeError("synthetic recovery demonstration failed")
            return result
