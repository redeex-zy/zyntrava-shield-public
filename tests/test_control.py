import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zyntrava.api import create_app
from zyntrava.control import Control
from zyntrava.models import ToolRequest

ADMIN = "operator-fixture-credential-00000000000"
AGENT = "agent-fixture-credential-0000000000000"


@pytest.fixture
def controlled(broker, tmp_path):
    control = Control(Path.cwd(), tmp_path / "control", broker)
    with TestClient(
        create_app(
            broker, admin_token=ADMIN, agent_token=AGENT, authority="testserver", control=control
        )
    ) as client:
        yield client, control


def test_control_roles_and_closed_settings(controlled):
    client, control = controlled
    for route in ["/settings", "/integrations", "/research/results", "/research/jobs", "/tasks"]:
        assert client.get(route, headers={"Authorization": f"Bearer {AGENT}"}).status_code == 403
    headers = {"Authorization": f"Bearer {ADMIN}"}
    assert (
        client.put("/settings", headers=headers, json={"protection_mode": "off"}).status_code == 422
    )
    assert (
        client.put(
            "/settings",
            headers=headers,
            json={"retention_days": 14, "poll_seconds": 3, "protection_mode": "full"},
        ).status_code
        == 200
    )
    assert json.loads((control.state / "settings.json").read_text())["retention_days"] == 14
    assert client.get("/settings", headers=headers).json()["remote_access"] is False


def test_recovery_demo_records_verified_redacted_task_and_duplicate_prevention(controlled):
    client, control = controlled
    headers = {"Authorization": f"Bearer {ADMIN}"}
    assert client.get("/tasks", headers=headers).json() == []
    response = client.post("/research/jobs", json={"kind": "recovery-demo"}, headers=headers)
    assert response.status_code == 202
    for _ in range(200):
        job = client.get("/research/jobs", headers=headers).json()[0]
        if job["status"] not in {"queued", "running"}:
            break
        time.sleep(0.01)
    assert job["status"] == "completed"
    assert job["experiment_id"] is None  # A task demo produces task history, not a result file.
    assert job["error"] is None
    task = client.get("/tasks", headers=headers).json()[0]
    assert task["state"] == "verified" and task["claimed"] == 1
    assert task["recoveries"] == 1 and task["denials"] == 1
    assert not any(
        key in task for key in ("plan", "recipient", "payment", "session_id", "authorization")
    )
    assert "owned-simulator" not in json.dumps(task)
    assert (
        client.post(
            "/research/jobs",
            json={"kind": "recovery-demo"},
            headers={"Authorization": f"Bearer {AGENT}"},
        ).status_code
        == 403
    )


def test_isolated_trace_worker_completes_and_api_remains_responsive(controlled):
    client, control = controlled
    headers = {"Authorization": f"Bearer {ADMIN}"}
    response = client.post(
        "/research/jobs", json={"kind": "trace", "corpus_version": 1}, headers=headers
    )
    assert response.status_code == 202
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        assert client.get("/health").status_code == 200
        job = client.get("/research/jobs", headers=headers).json()[0]
        if job["status"] not in {"queued", "running"}:
            break
        time.sleep(0.02)
    assert job["status"] == "completed"
    assert control.trace_process is None
    assert (
        client.get(f"/research/results/{job['experiment_id']}", headers=headers).status_code == 200
    )


def test_policy_concurrency_and_pending_approval_invalidation(controlled, broker):
    client, _ = controlled
    headers = {"Authorization": f"Bearer {ADMIN}"}
    session = broker.create_session()
    pending = broker.submit(
        session,
        ToolRequest(
            tool="write_file", arguments={"path": "reports/review.txt", "content": "public report"}
        ),
    )
    current = client.get("/policy", headers=headers).json()
    request = {"expected_digest": current["digest"], "policy": current["policy"]}
    request["policy"]["name"] = "changed"
    assert client.put("/policy", json=request, headers=headers).status_code == 200
    assert client.put("/policy", json=request, headers=headers).status_code == 409
    result = client.post(f"/approvals/{pending.approval_id}", json={"allow": True}, headers=headers)
    assert result.json()["execution"] == "not_run"
    assert not (broker.tools.root / "reports/review.txt").exists()
    request["expected_digest"] = client.get("/policy", headers=headers).json()["digest"]
    request["policy"]["rules"][0]["path_prefix"] = "../escape"
    assert client.put("/policy", json=request, headers=headers).status_code == 422


def test_demo_job_records_real_enforcement_and_paginates(controlled):
    client, _ = controlled
    headers = {"Authorization": f"Bearer {ADMIN}"}
    response = client.post("/research/jobs", json={"kind": "demo"}, headers=headers)
    assert response.status_code == 202
    for _ in range(100):
        job = client.get("/research/jobs", headers=headers).json()[0]
        if job["status"] not in {"queued", "running"}:
            break
        time.sleep(0.01)
    assert job["status"] == "completed"
    overview = client.get("/overview", headers=headers).json()
    assert job["experiment_id"] is None  # Real events remain available without an experiment.
    assert job["error"] is None
    assert overview["evaluated_actions"] == 3
    assert overview["blocked_actions"] == 1 and overview["pending_approvals"] == 1
    page = client.get("/events/page?limit=1", headers=headers).json()
    assert page["next_cursor"] is not None
    next_page = client.get(
        f"/events/page?limit=1&before={page['next_cursor']}", headers=headers
    ).json()
    assert next_page["items"][0]["sequence"] < page["items"][0]["sequence"]
    assert client.get("/research/results/not-an-id", headers=headers).status_code == 400
    assert client.get("/robots.txt").text == "User-agent: *\nDisallow: /\n"
    filtered = client.get(
        "/events/page?tool=read_file&execution=not_run&status=blocked", headers=headers
    ).json()
    assert len(filtered["items"]) == 1
    assert filtered["items"][0]["decision"]["rule_ids"] == ["deny-private-read"]
    assert client.get("/events/page?tool=%27%20OR%201=1--", headers=headers).json()["items"] == []


def test_task_view_handles_in_progress_ledger_creation(controlled):
    from zyntrava.audit import AuditStore

    client, control = controlled
    AuditStore(control.state / "tasks.sqlite3")
    assert client.get("/tasks", headers={"Authorization": f"Bearer {ADMIN}"}).json() == []
