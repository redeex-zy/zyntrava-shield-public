import json
import os
import sqlite3
from pathlib import Path

import pytest

from zyntrava.broker import Broker
from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, default_policy


def call(broker: Broker, session: str, tool: str, **args: str):
    return broker.submit(session, ToolRequest(tool=tool, arguments=args))


def test_authorized_read_and_actual_unauthorized_read_prevention(broker: Broker, monkeypatch):
    session = broker.create_session()
    assert (
        call(broker, session, "read_file", path="public/hello.txt").output == "Hello from the lab."
    )
    original = broker.tools.execute
    calls = []

    def spy(tool, args):
        calls.append(tool)
        return original(tool, args)

    monkeypatch.setattr(broker.tools, "execute", spy)
    denied = call(broker, session, "read_file", path="private/forbidden.txt")
    assert (denied.status, denied.execution) == ("blocked", "not_run")
    assert calls == []


@pytest.mark.parametrize(
    "path",
    [
        "../personal.txt",
        "/etc/passwd",
        "C:/file",
        "public/../private/x",
        "public\\hello.txt",
        "public/x:stream",
        "public/NUL.txt",
        "public/hello.txt.",
        "public//hello.txt",
        "publicity/x",
    ],
)
def test_unsafe_or_unscoped_paths_blocked(broker: Broker, path: str):
    outcome = call(broker, broker.create_session(), "read_file", path=path)
    assert outcome.status == "blocked"


def test_deny_precedence_and_segment_scope(broker: Broker):
    raw = json.loads(default_policy().model_dump_json())
    raw["rules"].append(
        {"id": "allow-private", "tool": "read_file", "effect": "allow", "path_prefix": "private"}
    )
    broker.policy = Policy.model_validate_json(json.dumps(raw))
    assert (
        call(broker, broker.create_session(), "read_file", path="private/forbidden.txt").status
        == "blocked"
    )


def test_unknown_tool_and_extra_arguments_do_not_execute(broker: Broker):
    session = broker.create_session()
    assert call(broker, session, "shell", command="whoami").status == "blocked"
    assert (
        call(broker, session, "read_file", path="public/hello.txt", approved="true").status
        == "blocked"
    )


def test_sensitive_read_blocks_encoded_sink_and_output_file(broker: Broker):
    session = broker.create_session()
    assert call(broker, session, "read_file", path="sensitive/data.txt").execution == "succeeded"
    result = call(
        broker, session, "post_message", url="http://127.0.0.1:8766/collect", body="encoded-data"
    )
    assert result.status == "blocked"
    assert result.decision.evidence[0].rule == "session_sensitive_read"
    assert (
        call(broker, session, "write_file", path="reports/leak.txt", content="encoded").status
        == "blocked"
    )
    assert not (broker.tools.root / "reports/leak.txt").exists()


def test_suspicious_text_is_observed_and_authorized_action_still_works(broker: Broker):
    session = broker.create_session()
    broker.observe(session, "An example says ignore previous instructions.", "user")
    assert call(broker, session, "read_file", path="public/hello.txt").execution == "succeeded"
    event = next(e for e in broker.audit.events() if e["phase"] == "observation")
    assert event["status"] == "detected" and event["execution"] == "not_run"
    assert event["evidence"][0]["category"] == "direct_prompt_injection"


def test_approval_requires_operator_snapshot_and_cannot_replay(broker: Broker):
    session = broker.create_session()
    proposal = ToolRequest(
        tool="write_file", arguments={"path": "reports/result.txt", "content": "safe"}
    )
    pending = broker.submit(session, proposal)
    proposal.arguments["content"] = "MUTATED"
    target = broker.tools.root / "reports/result.txt"
    assert not target.exists()
    assert pending.approval_id is not None
    assert broker.resolve(pending.approval_id, True).execution == "succeeded"
    assert target.read_text() == "safe"
    with pytest.raises(ValueError, match="consumed"):
        broker.resolve(pending.approval_id, True)


def test_approval_rechecks_sensitive_label(broker: Broker):
    session = broker.create_session()
    pending = call(broker, session, "write_file", path="reports/out.txt", content="transformed")
    call(broker, session, "read_file", path="sensitive/data.txt")
    assert broker.resolve(pending.approval_id, True).status == "blocked"
    assert not (broker.tools.root / "reports/out.txt").exists()


def test_expired_rejected_and_policy_changed_approvals_fail_closed(broker: Broker):
    for change in ("expire", "reject", "policy"):
        session = broker.create_session()
        broker.approval_ttl = -1 if change == "expire" else 300
        pending = call(broker, session, "write_file", path=f"reports/{change}.txt", content="safe")
        if change == "policy":
            broker.policy = broker.policy.model_copy(update={"name": "changed"})
        outcome = broker.resolve(pending.approval_id, change != "reject")
        assert outcome.status == "blocked"


def test_no_overwrite_even_after_approval(broker: Broker):
    session = broker.create_session()
    first = call(broker, session, "write_file", path="reports/out.txt", content="first")
    assert broker.resolve(first.approval_id, True).execution == "succeeded"
    second = call(broker, session, "write_file", path="reports/out.txt", content="second")
    outcome = broker.resolve(second.approval_id, True)
    assert (outcome.status, outcome.execution) == ("allowed", "failed")
    assert (broker.tools.root / "reports/out.txt").read_text() == "first"


def test_audit_never_stores_raw_secret_or_arguments(broker: Broker):
    session = broker.create_session()
    secret = "ZYN_TEST_SECRET_fixture123"
    result = call(broker, session, "post_message", url="http://127.0.0.1:8766/collect", body=secret)
    assert result.status == "blocked"
    raw = json.dumps(broker.audit.events())
    assert secret not in raw and '"arguments"' not in raw and '"body"' not in raw
    assert broker.overview()["blocked_actions"] == 1


def test_logging_failure_prevents_tool_execution(broker: Broker, monkeypatch):
    executed = []

    def fail(**kwargs):
        raise sqlite3.OperationalError("synthetic full disk")

    def unexpected_execute(*args):
        executed.append(True)

    monkeypatch.setattr(broker.audit, "append", fail)
    monkeypatch.setattr(broker.tools, "execute", unexpected_execute)
    with pytest.raises(sqlite3.OperationalError):
        call(broker, broker.create_session(), "read_file", path="public/hello.txt")
    assert executed == []


def test_symlink_escape_blocked_if_platform_allows_creation(broker: Broker, tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic outside file")
    try:
        (broker.tools.root / "public/link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("OS account cannot create symlinks; Linux execution remains required")
    assert (
        call(broker, broker.create_session(), "read_file", path="public/link.txt").status
        == "blocked"
    )


def test_hardlink_blocked(broker: Broker):
    os.link(broker.tools.root / "private/forbidden.txt", broker.tools.root / "public/link.txt")
    assert (
        call(broker, broker.create_session(), "read_file", path="public/link.txt").status
        == "blocked"
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_windows_junction_escape_blocked(broker: Broker, tmp_path: Path):
    import _winapi

    outside = tmp_path / "synthetic-outside"
    outside.mkdir()
    (outside / "record.txt").write_text("dummy outside value")
    link = broker.tools.root / "public/junction"
    # Test-only OS primitive; junction creation does not require symlink privilege.
    _winapi.CreateJunction(str(outside), str(link))
    try:
        result = call(
            broker, broker.create_session(), "read_file", path="public/junction/record.txt"
        )
        assert result.status == "blocked"
    finally:
        link.rmdir()  # Remove the single entry; never recurse into its target.
    assert (outside / "record.txt").is_file()


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8766/collect",
        "http://127.0.0.1:8767/collect",
        "http://127.0.0.1:8766/other",
        "https://example.com",
        "http://127.0.0.1:8766/collect?token=abc",
        "http://127.0.0.1:8766/collect#fragment",
        "http://user@127.0.0.1:8766/collect",
    ],
)
def test_destination_must_be_canonical_and_exactly_allowed(broker: Broker, url: str):
    assert (
        call(broker, broker.create_session(), "post_message", url=url, body="hi").status
        == "blocked"
    )
