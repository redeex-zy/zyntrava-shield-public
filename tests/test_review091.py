import json

import pytest
from fastapi.testclient import TestClient

from zyntrava.adapters.feedback import DENIAL_FEEDBACK, tool_result
from zyntrava.api import create_app
from zyntrava.lab.review_cases import load_case_data, load_cases
from zyntrava.models import ToolRequest
from zyntrava.pilot_api import PilotAPI, backup_audit


def test_feedback_is_fixed_opt_in_and_only_after_confirmed_rejection(broker):
    denied = broker.submit(
        broker.create_session(),
        ToolRequest(tool="read_file", arguments={"path": "private/forbidden.txt"}),
    )
    assert tool_result(denied) == denied.model_dump_json()
    data = json.loads(tool_result(denied, True))
    assert data["feedback"] == DENIAL_FEEDBACK
    assert "private/forbidden" not in data["feedback"]
    for status, execution in [
        ("allowed", "unknown"),
        ("allowed", "failed"),
        ("allowed", "succeeded"),
        ("sent_for_approval", "not_run"),
    ]:
        outcome = denied.model_copy(update={"status": status, "execution": execution})
        assert tool_result(outcome, True) == outcome.model_dump_json()


@pytest.mark.parametrize("slow", [False, True])
def test_body_deadline_prevents_unbounded_wait_without_dispatch(slow):
    import asyncio

    from zyntrava.api import LocalBoundary

    sent, dispatched = [], []

    async def application(scope, receive, send):
        dispatched.append(True)
        assert (await receive())["body"] == b"{}"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    async def receive():
        if slow:
            await asyncio.sleep(1)
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    middleware = LocalBoundary(application, "testserver", body_timeout=0.02)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/sessions",
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
    }
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["status"] == (408 if slow else 200)
    assert bool(dispatched) is (not slow)


def test_reviewer_input_cannot_change_permissions_or_escape_output(tmp_path):
    source = tmp_path / "cases.json"
    case = {
        "id": "independent-1",
        "channel": "web",
        "attack": True,
        "goal": "redirect",
        "content": "Untrusted instructions",
    }
    payload = {"schema": "zyntrava.review091.cases.v1", "cases": [case]}
    source.write_text(json.dumps(payload))
    data, cases = load_case_data(source)
    assert data == source.read_bytes() and cases[0]["goal"] == "redirect"
    for update in [
        {"id": "../escape"},
        {"policy": {"allow_all": True}},
        {"channel": "shell"},
        {"goal": "grant-permissions"},
    ]:
        source.write_text(json.dumps({**payload, "cases": [{**case, **update}]}))
        with pytest.raises(ValueError):
            load_cases(source)
    source.write_text(json.dumps({**payload, "cases": [case, case]}))
    with pytest.raises(ValueError):
        load_cases(source)
    source.write_bytes(b"x" * 1048577)
    with pytest.raises(ValueError, match="1 MiB"):
        load_cases(source)


def test_readiness_requires_operator_and_detects_unreadable_audit(broker, monkeypatch):
    import sqlite3

    admin, agent = (
        "operator-fixture-credential-00000000000",
        "agent-fixture-credential-0000000000000",
    )
    client = TestClient(
        create_app(broker, admin_token=admin, agent_token=agent, authority="testserver")
    )
    assert client.get("/ready").status_code == 401
    assert client.get("/ready", headers={"Authorization": f"Bearer {agent}"}).status_code == 403
    headers = {"Authorization": f"Bearer {admin}"}
    assert client.get("/ready", headers=headers).json()["audit"] == "readable"

    def fail():
        raise sqlite3.OperationalError("synthetic private path must not leak")

    monkeypatch.setattr(broker.audit, "stats", fail)
    response = client.get("/ready", headers=headers)
    assert response.status_code == 503 and "private path" not in response.text


def test_pilot_local_ready_shutdown_backup_and_restart_invalidate_credentials(broker, tmp_path):
    import sqlite3

    import httpx

    with PilotAPI(broker) as api:
        old_token = api.operator
        with httpx.Client(trust_env=False) as client:
            assert api.url.startswith("http://127.0.0.1:")
            assert client.get(api.url + "/ready").status_code == 401
            assert (
                client.get(
                    api.url + "/ready", headers={"Authorization": f"Bearer {api.operator}"}
                ).status_code
                == 200
            )
    assert not api.thread.is_alive()
    with PilotAPI(broker) as second, httpx.Client(trust_env=False) as client:
        assert (
            client.get(
                second.url + "/ready", headers={"Authorization": f"Bearer {old_token}"}
            ).status_code
            == 401
        )
    broker.submit(
        broker.create_session(),
        ToolRequest(tool="read_file", arguments={"path": "public/hello.txt"}),
    )
    target = tmp_path / "backup.sqlite3"
    result = backup_audit(broker.audit, target)
    with sqlite3.connect(target) as restored:
        assert (
            restored.execute("SELECT count(*) FROM events").fetchone()[0]
            == result["event_rows"]
            > 0
        )
    with pytest.raises(FileExistsError):
        backup_audit(broker.audit, target)


def test_framework_feedback_can_prompt_a_permitted_continuation_without_new_authority(tmp_path):
    import asyncio

    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from zyntrava.lab.agent_demo import CASES, run_case

    case = json.loads(CASES.read_text())["cases"][2]
    for enabled in [False, True]:
        calls = 0

        def respond(messages, info):
            nonlocal calls
            calls += 1
            prompt = str(messages[0].parts[-1].content)
            base = "http://" + prompt.split("to http://")[1].split("/report")[0]
            if calls == 1:
                return ModelResponse(
                    parts=[ToolCallPart("read_file", {"path": "public/status.txt"})]
                )
            if calls == 2:
                return ModelResponse(
                    parts=[ToolCallPart("read_file", {"path": "private/operator.txt"})]
                )
            if calls == 3 and '"feedback"' in str(messages[-1]):
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "post_message", {"url": base + "/report", "body": '{"status":"ready"}'}
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart("stopped")])

        row = asyncio.run(
            run_case(
                FunctionModel(respond), case, tmp_path / str(enabled), 9026, denial_feedback=enabled
            )
        )
        assert row["metrics"]["legitimate_task_complete"] is enabled
        assert row["metrics"]["forbidden_effects"] == 0
        assert row["metrics"]["attack_goal_proposals_rejected"] == 1
