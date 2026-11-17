import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zyntrava.adapters.pydantic_agent import run_agent
from zyntrava.api import create_app
from zyntrava.lab.environment import receiver
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, default_policy


def test_final_answer_opaque_leak_is_withheld_after_sensitive_tool(broker):
    calls = 0

    def model(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart("read_file", {"path": "sensitive/data.txt"})])
        return ModelResponse(parts=[TextPart("encoded opaque derived secret")])

    assert (
        run_agent(FunctionModel(model), broker, "Read the file.")
        == "Final answer withheld by policy."
    )
    event = next(e for e in broker.audit.events() if e["phase"] == "answer_decision")
    assert event["status"] == "blocked" and event["execution"] == "not_run"
    assert "encoded opaque" not in json.dumps(broker.audit.events())


def test_public_answer_allowed_but_audit_failure_releases_nothing(broker, monkeypatch):
    sid = broker.create_session()
    assert broker.final_answer(sid, "Public status").output == "Public status"

    def fail(**fields):
        raise sqlite3.OperationalError("dummy audit unavailable")

    monkeypatch.setattr(broker.audit, "append", fail)
    with pytest.raises(sqlite3.OperationalError):
        broker.final_answer(sid, "must not be released")


def test_agent_credential_cannot_reset_taint_or_borrow_operator_session(broker):
    admin, agent = "synthetic-operator-credential-000000", "synthetic-agent-credential-00000000"
    app = create_app(broker, admin_token=admin, agent_token=agent, authority="testserver")
    headers = {"Authorization": "Bearer " + agent}
    with TestClient(app) as client:
        sid = client.post("/sessions", json={}, headers=headers).json()["session_id"]
        result = client.post(
            f"/sessions/{sid}/actions",
            headers=headers,
            json={"tool": "read_file", "arguments": {"path": "sensitive/data.txt"}},
        )
        assert result.json()["execution"] == "succeeded"
        assert client.post("/sessions", json={}, headers=headers).json()["session_id"] == sid
        other = client.post(
            "/sessions", json={}, headers={"Authorization": "Bearer " + admin}
        ).json()["session_id"]
        assert (
            client.post(
                f"/sessions/{other}/actions",
                headers=headers,
                json={"tool": "read_file", "arguments": {"path": "public/hello.txt"}},
            ).status_code
            == 403
        )


def test_count_budget_survives_new_sessions_policy_reload_and_failed_input(broker):
    with receiver() as (server, endpoint):
        raw = json.loads(default_policy(endpoint).model_dump_json())
        raw["release_rules"] = [
            {
                "id": "one-release",
                "source": "sensitive/records.json",
                "destination": endpoint,
                "max_records": 8,
            }
        ]
        broker.policy = Policy.model_validate_json(json.dumps(raw))
        source = broker.tools.root / "sensitive/records.json"
        source.write_text('{"schema":"zyntrava.records.v1","records":[]}', encoding="utf-8")
        proposal = ToolRequest(
            tool="export_count", arguments={"path": "sensitive/records.json", "url": endpoint}
        )
        assert broker.submit(broker.create_session(), proposal).execution == "succeeded"
        broker.policy = Policy.model_validate_json(json.dumps(raw))
        source.write_text("invalid second version", encoding="utf-8")
        denied = broker.submit(broker.create_session(), proposal)
        assert denied.status == "blocked" and denied.execution == "not_run"
        assert len(server.received) == 1
        assert denied.decision.evidence[0].rule == "release_budget"


def test_unregistered_tool_is_not_executed(broker):
    result = broker.submit(
        broker.create_session(), ToolRequest(tool="shell", arguments={"command": "dummy"})
    )
    assert result.status == "blocked" and result.execution == "not_run"


def test_failed_count_consumes_budget_before_source_validation(broker):
    with receiver() as (server, endpoint):
        raw = json.loads(default_policy(endpoint).model_dump_json())
        raw["release_rules"] = [
            {"id": "bounded-invalid", "source": "sensitive/records.json", "destination": endpoint}
        ]
        broker.policy = Policy.model_validate_json(json.dumps(raw))
        path = broker.tools.root / "sensitive/records.json"
        path.write_text("invalid", encoding="utf-8")
        proposal = ToolRequest(
            tool="export_count", arguments={"path": "sensitive/records.json", "url": endpoint}
        )
        assert broker.submit(broker.create_session(), proposal).execution == "failed"
        path.write_text('{"schema":"zyntrava.records.v1","records":[]}', encoding="utf-8")
        result = broker.submit(broker.create_session(), proposal)
        assert result.status == "blocked" and server.received == []
