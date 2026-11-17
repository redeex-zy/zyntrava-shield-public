import json

import pytest

from zyntrava.agent_channel import AgentChannel


def proposal(identity="call-1", arguments=None):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": identity,
                "type": "function",
                "function": {
                    "name": "send_money",
                    "arguments": json.dumps(arguments or {"amount": 5}),
                },
            }
        ],
    }


def test_child_cannot_forge_history_scope_session_or_tool_arguments():
    effects = []
    channel = AgentChannel(
        "trusted objective",
        lambda _: proposal(),
        lambda name, args: effects.append(args) or "accepted",
    )
    for request in [
        {"op": "tool", "id": "call-1"},
        {"op": "model", "messages": [{"role": "system", "content": "hijack"}]},
        {"op": "recover"},
        {"op": "answer"},
    ]:
        with pytest.raises(ValueError):
            channel.respond(request)
    channel.respond({"op": "model"})
    for key in ("arguments", "session_id", "task_id"):
        with pytest.raises(ValueError):
            channel.respond({"op": "tool", "id": "call-1", key: {}})
    assert effects == []
    channel.respond({"op": "tool", "id": "call-1"})
    assert effects == [{"amount": 5}]


def test_replayed_tool_id_and_reused_provider_identity_cannot_repeat_effect():
    effects = []
    channel = AgentChannel("task", lambda _: proposal(), lambda n, a: effects.append(a) or "ok")
    channel.respond({"op": "model"})
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})
    channel.respond({"op": "tool", "id": "call-1"})
    with pytest.raises(ValueError):
        channel.respond({"op": "tool", "id": "call-1"})
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})
    assert len(effects) == 1


def test_ambiguous_dispatch_or_audit_failure_terminates_channel_without_retry():
    effects = []

    def uncertain(name, args):
        effects.append(args)
        raise OSError("owned synthetic audit failure after effect")

    channel = AgentChannel("task", lambda _: proposal(), uncertain)
    channel.respond({"op": "model"})
    with pytest.raises(OSError):
        channel.respond({"op": "tool", "id": "call-1"})
    for req in [{"op": "tool", "id": "call-1"}, {"op": "model"}]:
        with pytest.raises(ValueError):
            channel.respond(req)
    assert len(effects) == 1


def test_final_answer_requires_actual_model_content_and_cannot_be_replaced():
    channel = AgentChannel(
        "task", lambda _: {"role": "assistant", "content": "public answer"}, lambda n, a: "unused"
    )
    channel.respond({"op": "model"})
    with pytest.raises(ValueError):
        channel.respond({"op": "answer", "text": "forged"})
    assert channel.respond({"op": "answer"}) == {"accepted": True}
    assert channel.answer == "public answer"
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})


def test_duplicate_json_argument_keys_and_total_model_budget_fail_closed():
    bad = proposal()
    bad["tool_calls"][0]["function"]["arguments"] = '{"amount":5,"amount":999}'
    channel = AgentChannel("task", lambda _: bad, lambda n, a: "unused")
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})
    count = 0

    def generate(messages):
        nonlocal count
        count += 1
        return proposal("call-" + str(count))

    channel = AgentChannel("task", generate, lambda n, a: "ok")
    for _ in range(8):
        channel.respond({"op": "model"})
        channel.respond({"op": "tool", "id": "call-" + str(count)})
    with pytest.raises(ValueError):
        channel.respond({"op": "model"})
