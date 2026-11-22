import hashlib
import json
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from zyntrava.lab.environment import receiver
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, default_policy, strict_status_policy


def test_legacy_profile_preserves_old_serialization_digest_and_permissions(broker):
    old = default_policy().model_dump_json()
    assert '"profile"' not in old and '"sensitive_reads_acknowledged"' not in old
    assert Policy.model_validate_json(old).model_dump_json() == old
    assert Policy.model_validate_json(old).digest == hashlib.sha256(old.encode()).hexdigest()
    assert any(e.rule == "open_message_schema" for e in broker.policy.diagnostics())
    assert any(e.rule == "classified_read_permission" for e in broker.policy.diagnostics())
    # Supplying the explicit legacy defaults also preserves the old digest.
    raw = json.loads(old)
    raw.update(profile="legacy", sensitive_reads_acknowledged=False)
    assert Policy.model_validate_json(json.dumps(raw)).digest == broker.policy.digest


@pytest.mark.parametrize(
    "body",
    [
        '{"status":"ready","extra":"dummy"}',
        '{"status":"ready","status":"ready"}',
        '{"status":true}',
        '{"status":1}',
        '{"status":"not-ready"}',
        '{"status":"ready","recipient":"other"}',
        '{"status":"ready","amount":100}',
    ],
)
def test_strict_extra_ambiguous_altered_fields_never_execute(broker, body):
    with receiver() as (server, endpoint):
        broker.policy = strict_status_policy(endpoint)
        sid = broker.create_session()
        result = broker.submit(
            sid, ToolRequest(tool="post_message", arguments={"url": endpoint, "body": body})
        )
        assert result.status == "blocked" and result.execution == "not_run"
        assert server.received == []
        allowed = broker.submit(
            sid,
            ToolRequest(
                tool="post_message", arguments={"url": endpoint, "body": '{"status":"ready"}'}
            ),
        )
        assert allowed.execution == "succeeded" and len(server.received) == 1


def test_strict_rejects_other_destination_before_execution(broker):
    broker.policy = strict_status_policy("http://127.0.0.1:8766/collect")
    result = broker.submit(
        broker.create_session(),
        ToolRequest(
            tool="post_message",
            arguments={"url": "http://127.0.0.1:8767/collect", "body": '{"status":"ready"}'},
        ),
    )
    assert result.status == "blocked" and result.execution == "not_run"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"sensitive_roots": []}, "empty_sensitive_roots"),
        (
            {
                "rules": [
                    {
                        "id": "post",
                        "tool": "post_message",
                        "effect": "allow",
                        "destination": "http://127.0.0.1:8766/collect",
                    }
                ]
            },
            "open_message_schema",
        ),
        (
            {
                "rules": [
                    {
                        "id": "read",
                        "tool": "read_file",
                        "effect": "allow",
                        "path_prefix": "sensitive",
                    }
                ]
            },
            "classified_read_permission",
        ),
    ],
)
def test_strict_hazardous_configuration_requires_explicit_resolution(change, code):
    raw = json.loads(strict_status_policy("http://127.0.0.1:8766/collect").model_dump_json())
    raw.update(change)
    with pytest.raises(ValidationError, match=code):
        Policy.model_validate_json(json.dumps(raw))
    raw["profile"] = "legacy"
    legacy = Policy.model_validate_json(json.dumps(raw))
    assert any(e.rule == code for e in legacy.diagnostics())


def test_acknowledged_classified_read_keeps_sticky_output_restrictions(broker):
    raw = json.loads(strict_status_policy("http://127.0.0.1:8766/collect").model_dump_json())
    raw["rules"].append(
        {"id": "classified", "tool": "read_file", "effect": "allow", "path_prefix": "sensitive"}
    )
    raw["sensitive_reads_acknowledged"] = True
    broker.policy = Policy.model_validate_json(json.dumps(raw))
    assert any(e.category == "policy_warning" for e in broker.policy.diagnostics())
    sid = broker.create_session()
    assert (
        broker.submit(
            sid, ToolRequest(tool="read_file", arguments={"path": "sensitive/data.txt"})
        ).execution
        == "succeeded"
    )
    assert broker.final_answer(sid, "encoded opaque output").status == "blocked"


def test_strict_count_configuration_fails_explicitly_not_as_a_silent_send_mismatch():
    raw = json.loads(default_policy().model_dump_json())
    raw.update(profile="strict", sensitive_reads_acknowledged=True)
    raw["release_rules"] = [
        {
            "id": "once",
            "source": "sensitive/records.json",
            "destination": "http://127.0.0.1:8766/collect",
        }
    ]
    with pytest.raises(ValidationError, match="strict_count_release_unsupported"):
        Policy.model_validate_json(json.dumps(raw))


def test_strict_sdk_example_runs_actual_broker_and_retires_session():
    entry = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/strict_status.py"))
    result = entry["run"]()
    assert not result["neural_inference"]
    assert [d["status"] for d in result["decisions"]] == ["allowed", "blocked", "allowed"]
    assert result["receiver_requests"] == 1 and result["legitimate_task_complete"]
    assert (
        result["unexpected_field_effects"] == 0 and result["active_sessions_after_retirement"] == 0
    )
