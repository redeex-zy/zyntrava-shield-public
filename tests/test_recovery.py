import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from zyntrava.agent_channel import AgentChannel
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.lab.receipts import PaymentTools, ReceiptBank
from zyntrava.models import PostArgs, ReadArgs, ToolRequest
from zyntrava.policy import Policy, Rule
from zyntrava.recovery import TaskController, TaskPlan


@pytest.fixture
def task(tmp_path):
    (tmp_path / "public").mkdir()
    (tmp_path / "public/bill.txt").write_text("Untrusted invoice document.")
    bank = ReceiptBank(tmp_path / "bank.db", {"transactions": []})
    with bank.serve() as url:
        policy = Policy(
            version=1,
            name="task-test",
            rules=(
                Rule(id="source", tool="read_file", effect="allow", path_prefix="public"),
                Rule(
                    id="payment",
                    tool="post_message",
                    effect="allow",
                    destination=url,
                    body_fields=(("recipient", "owned"), ("amount", 98.7)),
                ),
            ),
        )
        broker = Broker(
            policy,
            PaymentTools(tmp_path, "invoice-1", url),
            AuditStore(tmp_path / "audit.db"),
            simulated=True,
        )
        session = broker.create_session()
        plan = TaskPlan(
            task_id="task-1",
            authorization_id="invoice-1",
            session_id=session,
            policy_digest=policy.digest,
            source=ReadArgs(path="public/bill.txt"),
            payment=PostArgs(url=url, body=json.dumps({"recipient": "owned", "amount": 98.7})),
            expires_at=time.time() + 300,
        )
        controller = TaskController(broker, tmp_path / "tasks.db", bank.verify)
        controller.register(plan)
        yield controller, broker, bank, plan


def read(controller, plan):
    return controller.submit(
        plan.task_id,
        plan.session_id,
        ToolRequest(tool="read_file", arguments=plan.source.model_dump()),
    )


def pay(controller, plan, **updates):
    body = dict(json.loads(plan.payment.body), **updates)
    return controller.submit(
        plan.task_id,
        plan.session_id,
        ToolRequest(
            tool="post_message", arguments={"url": plan.payment.url, "body": json.dumps(body)}
        ),
    )


@pytest.mark.parametrize(
    "fault,state", [("none", "verified"), ("unavailable-receipt", "uncertain")]
)
def test_live_channel_binding_keeps_duplicate_and_uncertain_effect_protection(task, fault, state):
    controller, _, bank, plan = task
    read(controller, plan)
    bank.fault = fault
    item = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "owned-call",
                "type": "function",
                "function": {
                    "name": "post_message",
                    "arguments": json.dumps(plan.payment.model_dump()),
                },
            }
        ],
    }
    channel = AgentChannel(
        "operator task",
        lambda _: item,
        lambda name, args: controller.submit(
            plan.task_id, plan.session_id, ToolRequest(tool=name, arguments=args)
        ).model_dump_json(),
    )
    channel.respond({"op": "model"})
    with pytest.raises(ValueError):
        channel.respond({"op": "tool", "id": "owned-call", "session_id": "foreign"})
    assert bank.posts == 0
    channel.respond({"op": "tool", "id": "owned-call"})
    with pytest.raises(ValueError):
        channel.respond({"op": "tool", "id": "owned-call"})
    controller.recover(plan.task_id)
    assert controller.status(plan.task_id)["state"] == state
    assert bank.posts == 1 and len(bank.state()["transactions"]) == 1


def test_channel_audit_failure_cannot_be_retried_or_expand_scope(task, monkeypatch):
    controller, broker, bank, plan = task
    read(controller, plan)
    item = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "bad-call",
                "type": "function",
                "function": {
                    "name": "post_message",
                    "arguments": json.dumps(
                        {"url": plan.payment.url, "body": '{"recipient":"attacker","amount":1000}'}
                    ),
                },
            }
        ],
    }

    def fail(**kwargs):
        raise OSError("synthetic audit unavailable")

    monkeypatch.setattr(broker.audit, "append", fail)
    channel = AgentChannel(
        "task",
        lambda _: item,
        lambda name, args: controller.submit(
            plan.task_id, plan.session_id, ToolRequest(tool=name, arguments=args)
        ).model_dump_json(),
    )
    channel.respond({"op": "model"})
    with pytest.raises(OSError):
        channel.respond({"op": "tool", "id": "bad-call"})
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})
    assert bank.posts == 0 and bank.state()["transactions"] == []


def test_recovery_keeps_authority_and_verifies_one_real_effect(task):
    controller, _, bank, plan = task
    assert read(controller, plan).execution == "succeeded"
    assert pay(controller, plan, recipient="attacker").status == "blocked"
    assert controller.recover(plan.task_id)["state"] == "verified"
    assert bank.state()["transactions"] == [{"recipient": "owned", "amount": 98.7}]
    assert pay(controller, plan).status == "blocked"
    assert controller.recover(plan.task_id)["recoveries"] == 1
    assert bank.posts == 1


@pytest.mark.parametrize(
    "fault,expected,effects",
    [
        ("reject-before-effect", "uncertain", 0),
        ("drop-after-effect", "verified", 1),
        ("unavailable-receipt", "uncertain", 1),
        ("malicious-error", "uncertain", 0),
    ],
)
def test_uncertain_or_failed_payment_never_automatically_retries(task, fault, expected, effects):
    controller, _, bank, plan = task
    read(controller, plan)
    bank.fault = fault
    pay(controller, plan)
    assert controller.status(plan.task_id)["state"] == expected
    controller.recover(plan.task_id)
    pay(controller, plan)
    assert bank.posts == 1
    assert len(bank.state()["transactions"]) == effects
    bank.fault = "none"
    if effects:
        assert controller.reconcile(plan.task_id) == "verified"
    assert bank.posts == 1


@pytest.mark.parametrize("change", ["expiry", "policy", "cancel", "foreign-session"])
def test_stale_cancelled_and_cross_session_authority_cannot_dispatch(task, change):
    controller, broker, bank, plan = task
    read(controller, plan)
    if change == "expiry":
        with controller.ledger.connect() as conn:
            expired = plan.model_copy(update={"expires_at": time.time() - 1})
            conn.execute("UPDATE tasks SET plan=?", (expired.model_dump_json(),))
    elif change == "policy":
        broker.policy = broker.policy.model_copy(update={"name": "revoked"})
    elif change == "cancel":
        assert controller.cancel(plan.task_id)
    else:
        other = broker.create_session()
        result = controller.submit(
            plan.task_id,
            other,
            ToolRequest(tool="post_message", arguments=plan.payment.model_dump()),
        )
        assert result.status == "blocked"
        assert bank.posts == 0
        return
    assert pay(controller, plan).status == "blocked"
    controller.recover(plan.task_id)
    assert bank.posts == 0


def test_duplicate_authorization_and_concurrent_payment_are_single_effect(task):
    controller, broker, bank, plan = task
    with pytest.raises(sqlite3.IntegrityError):
        controller.register(
            plan.model_copy(
                update={"task_id": "another-task", "session_id": broker.create_session()}
            )
        )
    read(controller, plan)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: pay(controller, plan), range(8)))
    assert sum(o.execution == "succeeded" for o in outcomes) == 1
    assert len(bank.state()["transactions"]) == bank.posts == 1


def test_ledger_restart_and_unknown_broker_session_do_not_replay(task):
    controller, broker, bank, plan = task
    read(controller, plan)
    pay(controller, plan)
    restarted = TaskController(broker, controller.ledger.path, bank.verify)
    assert restarted.recover(plan.task_id)["state"] == "verified"
    assert pay(restarted, plan).status == "blocked"
    assert bank.posts == 1
    broker._sessions.clear()
    assert pay(restarted, plan).status == "blocked"
    assert bank.posts == 1


def test_recovery_does_not_clear_classification_or_grant_alternate_tools(task):
    controller, broker, bank, plan = task
    read(controller, plan)
    broker.observe(plan.session_id, "ZYN_TEST_SECRET_protected_recovery_fixture", "user")
    controller.submit(
        plan.task_id, plan.session_id, ToolRequest(tool="native_transfer", arguments={})
    )
    controller.recover(plan.task_id)
    assert bank.posts == 0
    assert broker.final_answer(plan.session_id, "opaque protected output").status == "blocked"


def test_missing_source_stops_and_approval_cannot_be_invented(task):
    controller, broker, bank, plan = task
    (broker.tools.root / plan.source.path).unlink()
    assert read(controller, plan).execution == "failed"
    assert controller.recover(plan.task_id)["state"] == "stopped"
    assert bank.posts == 0


def test_pre_effect_audit_failure_consumes_payment_claim(task, monkeypatch):
    controller, broker, bank, plan = task
    read(controller, plan)
    original = broker.audit.append

    def fail(**fields):
        raise OSError("synthetic unavailable audit")

    monkeypatch.setattr(broker.audit, "append", fail)
    with pytest.raises(OSError):
        pay(controller, plan)
    monkeypatch.setattr(broker.audit, "append", original)
    controller.reconcile(plan.task_id)
    assert pay(controller, plan).status == "blocked"
    assert bank.posts == 0


def test_operator_cancel_after_verified_payment_reports_too_late(task):
    controller, _, bank, plan = task
    read(controller, plan)
    pay(controller, plan)
    assert not controller.cancel(plan.task_id)
    assert controller.status(plan.task_id)["state"] == "verified"
    assert bank.posts == 1


def test_recovery_reports_committed_stop_and_preserves_classification(task):
    controller, broker, bank, plan = task
    read(controller, plan)
    pay(controller, plan, amount=198.7)
    broker.policy = broker.policy.model_copy(update={"name": "changed-after-denial"})
    result = controller.recover(plan.task_id)
    assert result["state"] == "stopped"
    assert result["reason"] == "policy_revoked"
    assert bank.posts == 0


def test_adaptive_wrong_actions_exhaust_budget_without_effect(task):
    controller, _, bank, plan = task
    read(controller, plan)
    for amount in range(20):
        assert pay(controller, plan, amount=float(amount)).status == "blocked"
    assert controller.recover(plan.task_id)["state"] == "stopped"
    assert bank.posts == 0


def test_forged_receipt_and_changed_idempotency_payload_are_not_success(task):
    controller, _, bank, plan = task
    read(controller, plan)
    bank.apply(plan.authorization_id, json.dumps({"recipient": "attacker", "amount": 1.0}))
    assert bank.verify(plan.authorization_id, plan.payment) == "conflict"
    pay(controller, plan)
    assert controller.status(plan.task_id)["state"] == "uncertain"
    assert len(bank.state()["transactions"]) == 1
    assert bank.posts == 1


def test_success_response_without_new_payment_is_not_verified(task):
    controller, _, bank, plan = task
    # A pre-existing transaction must not act as proof of this new payment.
    with bank.store.connect() as conn:
        conn.execute(
            "UPDATE state SET value=?",
            (json.dumps({"transactions": [{"recipient": "old", "amount": 1.0}]}),),
        )
    bank.mutate = lambda state, payload: (state, {"claimed_success": True})
    read(controller, plan)
    assert pay(controller, plan).execution == "succeeded"  # Transport success only.
    assert controller.status(plan.task_id)["state"] == "uncertain"
    assert bank.verify(plan.authorization_id, plan.payment) == "conflict"
    assert len(bank.state()["transactions"]) == 1
