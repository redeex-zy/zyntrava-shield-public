"""Operator/API regressions: no sleeps, real exclusive-create side effects."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from test_api import ADMIN, AGENT, auth

from zyntrava.api import create_app
from zyntrava.models import ToolRequest


@pytest.fixture
def client(broker):
    return TestClient(
        create_app(broker, admin_token=ADMIN, agent_token=AGENT, authority="testserver")
    )


def pending(broker):
    return broker.submit(
        broker.create_session(),
        ToolRequest(tool="write_file", arguments={"path": "reports/once.txt", "content": "once"}),
    ).approval_id


def test_only_operator_can_consume_and_only_once(client, broker):
    url = f"/approvals/{pending(broker)}"
    assert client.post(url, headers=auth(AGENT), json={"allow": True}).status_code == 403
    assert (
        client.post(url, headers=auth(ADMIN), json={"allow": True}).json()["execution"]
        == "succeeded"
    )
    assert client.post(url, headers=auth(ADMIN), json={"allow": True}).status_code == 400
    assert (broker.tools.root / "reports/once.txt").read_text() == "once"


def test_expired_approval_cannot_execute_or_be_reused(client, broker, monkeypatch):
    monkeypatch.setattr("zyntrava.broker.time.monotonic", lambda: 100.0)
    url = f"/approvals/{pending(broker)}"
    monkeypatch.setattr("zyntrava.broker.time.monotonic", lambda: 401.0)
    outcome = client.post(url, headers=auth(ADMIN), json={"allow": True}).json()
    assert outcome["execution"] == "not_run" and outcome["status"] == "blocked"
    assert client.post(url, headers=auth(ADMIN), json={"allow": True}).status_code == 400
    assert not (broker.tools.root / "reports/once.txt").exists()


def test_expired_listing_and_concurrent_resolution_fail_closed(client, broker, monkeypatch):
    monkeypatch.setattr("zyntrava.broker.time.monotonic", lambda: 100.0)
    approval = pending(broker)
    monkeypatch.setattr("zyntrava.broker.time.monotonic", lambda: 401.0)
    assert client.get("/approvals", headers=auth(ADMIN)).json() == []
    assert (
        client.post(f"/approvals/{approval}", headers=auth(ADMIN), json={"allow": True}).status_code
        == 400
    )
    approval = pending(broker)

    def resolve(_):
        return client.post(f"/approvals/{approval}", headers=auth(ADMIN), json={"allow": True})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(resolve, range(2)))
    assert sorted(r.status_code for r in results) == [200, 400]
    assert (broker.tools.root / "reports/once.txt").read_text() == "once"


def test_approval_audit_failure_consumes_grant_without_side_effect(broker, monkeypatch):
    approval = pending(broker)
    original = broker.audit.append

    def unavailable(**kwargs):
        raise sqlite3.OperationalError("synthetic unavailable audit")

    monkeypatch.setattr(broker.audit, "append", unavailable)
    with pytest.raises(sqlite3.OperationalError):
        broker.resolve(approval, True)
    assert not (broker.tools.root / "reports/once.txt").exists()
    monkeypatch.setattr(broker.audit, "append", original)
    with pytest.raises(ValueError):
        broker.resolve(approval, True)
