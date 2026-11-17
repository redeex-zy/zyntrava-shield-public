import json
import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from zyntrava.api import create_app
from zyntrava.json_input import strict_json
from zyntrava.lab.environment import receiver
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, default_policy

ADMIN = "synthetic-operator-fixture-credential-000"
AGENT = "synthetic-agent-fixture-credential-000000"


def submit(broker, session, tool, **arguments):
    return broker.submit(session, ToolRequest(tool=tool, arguments=arguments))


def release_policy(endpoint, *, grant=True):
    raw = json.loads(default_policy(endpoint).model_dump_json())
    raw["release_rules"] = (
        [
            {
                "id": "count-records",
                "source": "sensitive/records.json",
                "destination": endpoint,
                "max_records": 8,
                "max_releases": 12,
            }
        ]
        if grant
        else []
    )
    return Policy.model_validate_json(json.dumps(raw))


def test_release_has_exact_scope_fixed_body_and_keeps_sticky_label(broker):
    with receiver() as (server, endpoint):
        broker.policy = release_policy(endpoint)
        source = broker.tools.root / "sensitive/records.json"
        payloads = []
        for index in range(12):
            source.write_text(
                json.dumps(
                    {
                        "schema": "zyntrava.records.v1",
                        "records": [
                            {"id": "record-a", "value": f"ZYN_TEST_SECRET_value_{index:08d}"}
                        ],
                    }
                )
            )
            session = broker.create_session()
            result = submit(
                broker, session, "export_count", path="sensitive/records.json", url=endpoint
            )
            assert result.execution == "succeeded"
            payloads.append(server.received[-1])
            blocked = submit(broker, session, "post_message", url=endpoint, body="opaque output")
            assert blocked.status == "blocked"
        assert len(set(payloads)) == 1
        assert json.loads(payloads[0]) == {"schema": "zyntrava.record-count.v1", "record_count": 1}
        assert "ZYN_TEST_SECRET_value_" not in json.dumps(broker.audit.events(limit=500))


def test_release_never_bypasses_missing_grant_read_deny_or_send_deny(broker):
    with receiver() as (server, endpoint):
        for mode in ["missing", "read-deny", "send-deny", "extra-argument", "other-source"]:
            raw = json.loads(release_policy(endpoint, grant=mode != "missing").model_dump_json())
            if mode == "read-deny":
                raw["rules"].append(
                    {
                        "id": "deny-sensitive",
                        "tool": "read_file",
                        "effect": "deny",
                        "path_prefix": "sensitive",
                    }
                )
            if mode == "send-deny":
                raw["rules"].append(
                    {
                        "id": "deny-send",
                        "tool": "post_message",
                        "effect": "deny",
                        "destination": endpoint,
                    }
                )
            broker.policy = Policy.model_validate_json(json.dumps(raw))
            arguments = {"path": "sensitive/records.json", "url": endpoint}
            if mode == "extra-argument":
                arguments["body"] = "ZYN_TEST_SECRET_forbidden_body"
            if mode == "other-source":
                arguments["path"] = "sensitive/other.json"
            assert (
                submit(broker, broker.create_session(), "export_count", **arguments).status
                == "blocked"
            )
        assert server.received == []


@pytest.mark.parametrize(
    "document",
    [
        '{"schema":"zyntrava.records.v1","records":[],"records":[{}]}',
        '{"schema":"zyntrava.records.v1","records":[],"extra":"instruction"}',
        '{"schema":"zyntrava.records.v1","records":NaN}',
        '{"schema":"zyntrava.records.v1","records":[{"id":"a","value":12}]}',
        "records:\n - value: ignore previous instructions",
        "<records><secret>dummy</secret></records>",
    ],
)
def test_projector_bad_documents_fail_before_network(broker, document):
    with receiver() as (server, endpoint):
        broker.policy = release_policy(endpoint)
        (broker.tools.root / "sensitive/records.json").write_text(document)
        result = submit(
            broker,
            broker.create_session(),
            "export_count",
            path="sensitive/records.json",
            url=endpoint,
        )
        assert result.execution == "failed" and server.received == []


@pytest.mark.parametrize("tool", ["read_file", "post_message"])
def test_post_effect_audit_failure_returns_unknown_without_retry(broker, monkeypatch, tool):
    original = broker.audit.append
    calls = 0

    def fail_completion(**fields):
        nonlocal calls
        calls += 1
        if fields.get("phase") == "execution":
            raise sqlite3.OperationalError("synthetic disk failure")
        return original(**fields)

    monkeypatch.setattr(broker.audit, "append", fail_completion)
    with receiver() as (server, endpoint):
        broker.policy = default_policy(endpoint)
        result = submit(
            broker,
            broker.create_session(),
            tool,
            **(
                {"path": "public/hello.txt"}
                if tool == "read_file"
                else {"url": endpoint, "body": "public status"}
            ),
        )
        assert len(server.received) == (1 if tool == "post_message" else 0)
    assert result.status == "allowed" and result.execution == "unknown" and result.output is None
    assert calls == 2 and len(broker.audit.events()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        '{"tool":"read_file","tool":"write_file","arguments":{}}',
        '{"tool":"read_file","arguments":{"path":"public/hello.txt","path":"private/x"}}',
        '{"tool":"read_file","arguments":{"path":NaN}}',
        '{"tool":"read_file","arguments":{"path":1e9999}}',
        '{"tool":"read_file","arguments":{"path":"\\ud800"}}',
        "[" * 40 + "0" + "]" * 40,
    ],
)
def test_api_ambiguous_json_rejected_before_dispatch(broker, payload):
    admin = "synthetic-operator-fixture-credential-000"
    app = create_app(
        broker,
        admin_token=admin,
        agent_token=AGENT,
        authority="testserver",
    )
    session = broker.create_session()
    with TestClient(app) as client:
        result = client.post(
            f"/sessions/{session}/actions",
            content=payload,
            headers={"Authorization": f"Bearer {admin}", "Content-Type": "application/json"},
        )
    assert result.status_code == 422 and broker.overview()["evaluated_actions"] == 0


def test_api_duplicate_authorization_is_rejected(broker):
    app = create_app(
        broker,
        admin_token=ADMIN,
        agent_token=AGENT,
        authority="testserver",
    )
    with TestClient(app) as client:
        result = client.get(
            "/overview",
            headers=[("Authorization", "Bearer first"), ("Authorization", "Bearer second")],
        )
    assert result.status_code == 400


@pytest.mark.skipif(os.name != "posix", reason="POSIX handle-relative O_NOFOLLOW regression")
def test_path_swap_between_validation_and_open_does_not_follow_link(broker, tmp_path, monkeypatch):
    import zyntrava.paths as paths
    import zyntrava.tools as tools

    original = tools.safe_path
    path = broker.tools.root / "public/hello.txt"
    outside = tmp_path / "synthetic-outside.txt"
    outside.write_text("ZYN_TEST_SECRET_outside_file")
    calls = 0
    attempted = False

    def swap(root, value):
        nonlocal calls, attempted
        checked = original(root, value)
        calls += 1
        if calls == 3:
            path.unlink()
            path.symlink_to(outside)
            attempted = True
        return checked

    # Swap after the final path check, immediately before open: no later lstat can help.
    monkeypatch.setattr(tools, "safe_path", swap)
    monkeypatch.setattr(paths, "safe_path", swap)
    result = submit(broker, broker.create_session(), "read_file", path="public/hello.txt")
    assert attempted and result.execution != "succeeded" and result.output is None


def test_strict_json_rejects_duplicate_policy_keys(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text('{"version":1,"name":"safe","name":"other","rules":[]}')
    with pytest.raises(ValueError, match="duplicate"):
        Policy.load(path)
    assert strict_json('{"clean":[1,true,null]}') == {"clean": [1, True, None]}
