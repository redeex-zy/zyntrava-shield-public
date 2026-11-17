"""An explicit closed JSON permission stops extra-field effects without changing legacy rules."""

import pytest
from pydantic import ValidationError

from zyntrava.models import ToolRequest
from zyntrava.policy import Policy, Rule


def test_closed_keys_prevent_effect_but_keep_exact_report(broker):
    destination = "http://127.0.0.1:18766/report"
    rule = Rule(
        id="report",
        tool="post_message",
        effect="allow",
        destination=destination,
        body_fields=(("status", "ready"),),
        exact_body_fields=True,
    )
    broker.policy = Policy(version=1, name="exact", rules=(rule,))
    calls = []

    def execute(tool, args, **kwargs):
        calls.append(args.body)
        return "Executed fixture"

    broker.tools.execute = execute
    session = broker.create_session()
    for body in (
        '{"status":"ready","override":"attack"}',
        '{"status":"ready","status":"ready"}',
        '{"status":"degraded"}',
    ):
        result = broker.submit(
            session, ToolRequest(tool="post_message", arguments={"url": destination, "body": body})
        )
        assert result.status == "blocked" and result.execution == "not_run"
    assert calls == []
    result = broker.submit(
        session,
        ToolRequest(
            tool="post_message", arguments={"url": destination, "body": '{"status":"ready"}'}
        ),
    )
    assert result.execution == "succeeded" and len(calls) == 1


def test_legacy_serialization_and_extra_field_semantics_are_unchanged():
    rule = Rule(
        id="legacy",
        tool="post_message",
        effect="allow",
        destination="http://127.0.0.1:18766/report",
        body_fields=(("status", "ready"),),
    )
    assert "exact_body_fields" not in rule.model_dump()
    from zyntrava.models import PostArgs

    assert Policy._body_matches(
        rule, PostArgs(url=rule.destination, body='{"status":"ready","extra":"legacy"}')
    )
    with pytest.raises(ValidationError):
        Rule(
            id="invalid",
            tool="read_file",
            effect="allow",
            path_prefix="public",
            exact_body_fields=True,
        )
