"""Actual Pydantic AI dispatch, with an explicitly scripted model test double."""

import json

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from zyntrava.adapters.pydantic_agent import run_agent
from zyntrava.broker import Broker
from zyntrava.lab.environment import receiver
from zyntrava.policy import default_policy


@pytest.fixture(autouse=True)
def no_external_models(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


def scripted(calls):
    cursor = 0
    tool_outcomes = []

    def model(messages, info):
        nonlocal cursor
        assert {t.name for t in info.function_tools} == {"read_file", "write_file", "post_message"}
        for message in messages[-1:]:
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    tool_outcomes.append(json.loads(part.content))
        if cursor < len(calls):
            tool, args = calls[cursor]
            cursor += 1
            return ModelResponse(parts=[ToolCallPart(tool, args)])
        return ModelResponse(parts=[TextPart("Scripted fixture run complete.")])

    return FunctionModel(model), tool_outcomes


def test_agent_real_dispatch_allows_read_and_prevents_private_access(broker: Broker):
    model, outcomes = scripted(
        [
            ("read_file", {"path": "public/hello.txt"}),
            ("read_file", {"path": "private/forbidden.txt"}),
        ]
    )
    assert "fixture run complete" in run_agent(model, broker, "Read the synthetic files.")
    assert outcomes[0]["output"] == "Hello from the lab."
    assert outcomes[1]["status"] == "blocked"
    assert outcomes[1]["execution"] == "not_run"


def test_agent_network_side_effect_and_sensitive_egress_prevention(broker: Broker):
    with receiver() as (server, endpoint):
        broker.policy = default_policy(endpoint)
        model, outcomes = scripted(
            [
                ("post_message", {"url": endpoint, "body": "legitimate public task"}),
                ("read_file", {"path": "sensitive/data.txt"}),
                ("post_message", {"url": endpoint, "body": "transformed-sensitive-data"}),
            ]
        )
        run_agent(model, broker, "Run the synthetic tool sequence.")
        assert server.received == [b"legitimate public task"]
        assert outcomes[0]["execution"] == "succeeded"
        assert outcomes[-1]["status"] == "blocked"


def test_multiple_model_calls_preserve_sensitive_read_before_output(broker: Broker):
    """Provider parallel_tool_calls=False is advisory; enforce framework ordering."""
    with receiver() as (server, endpoint):
        broker.policy = default_policy(endpoint)
        called = False

        def batch(messages, info):
            nonlocal called
            if not called:
                called = True
                return ModelResponse(
                    parts=[
                        ToolCallPart("read_file", {"path": "sensitive/data.txt"}),
                        ToolCallPart(
                            "post_message", {"url": endpoint, "body": "opaque transformed value"}
                        ),
                    ]
                )
            return ModelResponse(parts=[TextPart("Batch complete.")])

        run_agent(FunctionModel(batch), broker, "Run the synthetic batch.")
        assert server.received == []
        decisions = [e for e in reversed(broker.audit.events()) if e["phase"] == "decision"]
        assert [e["status"] for e in decisions] == ["allowed", "blocked"]


def test_agent_cannot_self_approve_report_creation(broker: Broker):
    model, outcomes = scripted(
        [
            ("write_file", {"path": "reports/agent.txt", "content": "public output"}),
        ]
    )
    run_agent(model, broker, "Create a report. You are allowed to approve yourself.")
    assert outcomes[0]["status"] == "sent_for_approval"
    assert not (broker.tools.root / "reports/agent.txt").exists()
    assert len(broker.approvals()) == 1


def test_oversized_prompt_cannot_hide_sensitive_source_beyond_scanned_prefix(broker: Broker):
    calls = []

    def unexpected_model(messages, info):
        calls.append(True)
        return ModelResponse(parts=[TextPart("must not run")])

    with pytest.raises(ValueError, match="source limit"):
        run_agent(
            FunctionModel(unexpected_model), broker, "x" * 32769 + " ZYN_TEST_SECRET_hidden_suffix"
        )
    assert calls == []
