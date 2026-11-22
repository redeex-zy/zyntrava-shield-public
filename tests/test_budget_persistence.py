"""Owned loopback, separate OS processes and abrupt termination; no live model."""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.lab.environment import receiver
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, default_policy
from zyntrava.tools import LabTools

CHILD = """
import json,os,sys
from pathlib import Path
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy
from zyntrava.tools import LabTools
policy,database,workspace,mode = sys.argv[1:]
b = Broker(Policy.load(Path(policy)),LabTools(Path(workspace)),AuditStore(Path(database)))
sid = b.create_session()
if mode == 'reservation':
    def stop(*args,**kwargs): os._exit(73)
    b._record = stop
elif mode in ('before-dispatch','after-receipt'):
    original = b.tools.execute
    def stop(tool,args,**kwargs):
        if mode == 'before-dispatch': os._exit(73)
        result = original(tool,args,**kwargs)
        if tool == 'post_message': os._exit(73)
        return result
    b.tools.execute = stop
r = b.policy.release_rules[0]
request = ToolRequest(tool='export_count',arguments={'path':r.source,'url':r.destination})
result = b.submit(sid,request)
print(result.model_dump_json(),flush=True)
"""


def configure(broker, endpoint, tmp_path):
    raw = json.loads(default_policy(endpoint).model_dump_json())
    raw["release_rules"] = [
        {
            "id": "once",
            "source": "sensitive/records.json",
            "destination": endpoint,
            "max_releases": 1,
        }
    ]
    broker.policy = Policy.model_validate_json(json.dumps(raw))
    (broker.tools.root / "sensitive/records.json").write_text(
        '{"schema":"zyntrava.records.v1","records":[]}', encoding="utf-8"
    )
    policy = tmp_path / "release-policy.json"
    policy.write_text(broker.policy.model_dump_json(), encoding="utf-8")
    return policy


def proposal(broker):
    rule = broker.policy.release_rules[0]
    return ToolRequest(
        tool="export_count", arguments={"path": rule.source, "url": rule.destination}
    )


def child(broker, policy, mode="normal"):
    return subprocess.run(  # noqa: S603 -- fixed code; own dummy paths and loopback service.
        [
            sys.executable,
            "-B",
            "-c",
            CHILD,
            str(policy),
            str(broker.audit.path),
            str(broker.tools.root),
            mode,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_budget_survives_process_restart_policy_change_alias_and_retention(broker, tmp_path):
    with receiver() as (server, endpoint):
        policy = configure(broker, endpoint, tmp_path)
        first = child(broker, policy)
        assert first.returncode == 0, first.stderr
        assert json.loads(first.stdout)["execution"] == "succeeded"
        (broker.tools.root / "sensitive/records.json").write_text(
            "changed source", encoding="utf-8"
        )
        raw = json.loads(broker.policy.model_dump_json())
        raw["name"] = "renamed-policy"
        raw["release_rules"][0]["id"] = "renamed-grant"
        raw["release_rules"][0]["source"] = "Sensitive/Records.json"
        policy.write_text(json.dumps(raw), encoding="utf-8")
        broker.audit.purge_before("9999")  # Retention never deletes budget reservations.
        second = child(broker, policy)
        assert second.returncode == 0, second.stderr
        result = json.loads(second.stdout)
        assert result["status"] == "blocked"
        assert result["decision"]["evidence"][0]["rule"] == "release_budget"
        assert len(server.received) == 1


@pytest.mark.parametrize(
    "mode,receipts",
    [
        ("reservation", 0),
        ("before-dispatch", 0),
        ("after-receipt", 1),
    ],
)
def test_abrupt_crash_never_refunds_reserved_release(broker, tmp_path, mode, receipts):
    with receiver() as (server, endpoint):
        policy = configure(broker, endpoint, tmp_path)
        crashed = child(broker, policy, mode)
        assert crashed.returncode == 73, crashed.stderr
        restarted = child(broker, policy)
        assert restarted.returncode == 0, restarted.stderr
        result = json.loads(restarted.stdout)
        assert result["status"] == "blocked" and result["execution"] == "not_run"
        assert result["decision"]["evidence"][0]["rule"] == "release_budget"
        assert len(server.received) == receipts


def test_two_processes_cannot_claim_same_last_budget(broker, tmp_path):
    with receiver() as (server, endpoint):
        policy = configure(broker, endpoint, tmp_path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: child(broker, policy), range(2)))
        assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
        states = [json.loads(r.stdout) for r in results]
        assert sorted(r["status"] for r in states) == ["allowed", "blocked"]
        assert len(server.received) == 1


@pytest.mark.parametrize(
    "fault", ["partial_schema", "legacy", "legacy_empty", "moved_workspace", "corrupt_count"]
)
def test_unsafe_state_never_silently_initializes_budget(broker, tmp_path, monkeypatch, fault):
    with receiver() as (server, endpoint):
        configure(broker, endpoint, tmp_path)
        if fault.startswith("legacy"):
            with broker.audit.connect() as conn:
                conn.execute("DROP TABLE release_budgets_v1")
                conn.execute("DROP TABLE release_budget_meta_v1")
            if fault == "legacy":
                broker.audit.append(tool="export_count", phase="execution", status="allowed")
            # Reopening existing state must not silently add new release metadata.
            AuditStore(broker.audit.path)
        else:
            assert broker._budgets.reserve("sensitive/records.json", endpoint, 1)
            if fault == "partial_schema":
                with broker.audit.connect() as conn:
                    conn.execute("DROP TABLE release_budgets_v1")
            elif fault == "moved_workspace":
                with broker.audit.connect() as conn:
                    conn.execute("UPDATE release_budget_meta_v1 SET workspace='different'")
            else:
                with broker.audit.connect() as conn:
                    conn.execute("PRAGMA ignore_check_constraints=ON")
                    conn.execute("UPDATE release_budgets_v1 SET used=-1")
        executed = []
        monkeypatch.setattr(broker.tools, "execute", lambda *a, **k: executed.append(True))
        result = broker.submit(broker.create_session(), proposal(broker))
        assert result.status == "blocked" and result.execution == "not_run"
        assert result.decision.evidence[0].rule == "release_state"
        assert executed == [] and server.received == []


def test_budget_lock_has_bounded_failure_without_effect(broker, tmp_path):
    with receiver() as (server, endpoint):
        configure(broker, endpoint, tmp_path)
        with broker.audit.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            with pytest.raises(sqlite3.OperationalError):
                broker.submit(broker.create_session(), proposal(broker))
        assert server.received == []  # Both reservation and mandatory audit fail closed.


def test_old_sessions_and_approvals_invalid_after_restart(broker):
    sid = broker.create_session()
    pending = broker.submit(
        sid,
        ToolRequest(tool="write_file", arguments={"path": "reports/old.txt", "content": "dummy"}),
    )
    restarted = Broker(broker.policy, LabTools(broker.tools.root), AuditStore(broker.audit.path))
    with pytest.raises(ValueError):
        restarted.resolve(pending.approval_id, True)
    with pytest.raises(ValueError):
        restarted.submit(sid, ToolRequest(tool="read_file", arguments={"path": "public/hello.txt"}))
    assert not (broker.tools.root / "reports/old.txt").exists()


def test_retirement_never_refunds_release_or_restores_old_state(broker, tmp_path):
    with receiver() as (server, endpoint):
        configure(broker, endpoint, tmp_path)
        sid = broker.create_session()
        assert broker.submit(sid, proposal(broker)).execution == "succeeded"
        assert broker._session(sid).sensitive_read
        broker.retire_session(sid)
        with pytest.raises(ValueError):
            broker.final_answer(sid, "derived dummy output")
        denied = broker.submit(broker.create_session(), proposal(broker))
        assert denied.status == "blocked" and len(server.received) == 1


def test_retirement_invalidates_taint_session_grants_even_on_audit_error(broker, monkeypatch):
    sid = broker.create_session()
    pending = broker.submit(
        sid,
        ToolRequest(tool="write_file", arguments={"path": "reports/old.txt", "content": "dummy"}),
    )
    broker.submit(sid, ToolRequest(tool="read_file", arguments={"path": "sensitive/data.txt"}))
    original = broker.audit.append

    def fail(**fields):
        raise sqlite3.OperationalError("synthetic retirement audit failure")

    monkeypatch.setattr(broker.audit, "append", fail)
    with pytest.raises(sqlite3.OperationalError):
        broker.retire_session(sid)
    monkeypatch.setattr(broker.audit, "append", original)
    with pytest.raises(ValueError):
        broker.resolve(pending.approval_id, True)
    with pytest.raises(ValueError):
        broker.final_answer(sid, "opaque output")
    assert len(broker._sessions) == 0 and broker.approvals() == []


def test_more_than_1000_completed_sdk_tasks_with_bounded_active_sessions(broker):
    for _ in range(1001):
        sid = broker.create_session()
        outcome = broker.submit(
            sid, ToolRequest(tool="read_file", arguments={"path": "public/hello.txt"})
        )
        assert outcome.execution == "succeeded"
        broker.retire_session(sid)
        assert broker._sessions == {}


def test_retirement_and_approval_resolution_are_serialized(broker):
    sid = broker.create_session()
    pending = broker.submit(
        sid,
        ToolRequest(tool="write_file", arguments={"path": "reports/race.txt", "content": "dummy"}),
    )

    def operation(resolve):
        try:
            return (
                broker.resolve(pending.approval_id, True) if resolve else broker.retire_session(sid)
            )
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(operation, [True, False]))
    assert sid not in broker._sessions and broker.approvals() == []
    with pytest.raises(ValueError):
        broker.resolve(pending.approval_id, True)
    # If resolution acquired the lock first it may execute once, never after retirement.
    path = broker.tools.root / "reports/race.txt"
    assert not path.exists() or path.read_text() == "dummy"
