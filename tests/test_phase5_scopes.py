import json

import pytest

from zyntrava.models import PostArgs
from zyntrava.policy import Policy, Rule


def test_field_authorization_precedes_actual_network_effect(tmp_path):
    from zyntrava.audit import AuditStore
    from zyntrava.broker import Broker
    from zyntrava.lab.environment import receiver
    from zyntrava.models import ToolRequest
    from zyntrava.tools import LabTools

    with receiver() as (server, url):
        policy = Policy(
            version=1,
            name="bill",
            rules=(
                Rule(
                    id="one-recipient",
                    tool="post_message",
                    effect="allow",
                    destination=url,
                    body_fields=(("recipient", "owned"), ("amount", 98.7)),
                ),
            ),
        )
        broker = Broker(policy, LabTools(tmp_path), AuditStore(tmp_path / "audit.db"))
        session = broker.create_session()
        for recipient, expected in (("attacker", "blocked"), ("owned", "allowed")):
            outcome = broker.submit(
                session,
                ToolRequest(
                    tool="post_message",
                    arguments={
                        "url": url,
                        "body": json.dumps({"recipient": recipient, "amount": 98.7}),
                    },
                ),
            )
            assert outcome.status == expected
        assert len(server.received) == 1
        assert json.loads(server.received[0])["recipient"] == "owned"


@pytest.mark.parametrize(
    "body,allowed",
    [
        ('{"recipient":"owned","amount":98.7}', True),
        ('{"recipient":"attacker","amount":98.7}', False),
        ('{"recipient":"owned","amount":99.0}', False),
        ('{"recipient":"owned","amount":98.7,"amount":99.0}', False),
        ('{"recipient":"owned","amount":NaN}', False),
        ('{"recipient":"owned","amount":true}', False),
        ('{"recipient":"owned","amount":"98.7"}', False),
        ("[]", False),
    ],
)
def test_json_field_scope_is_exact_not_advisory(body: str, allowed: bool) -> None:
    rule = Rule(
        id="bill",
        tool="post_message",
        effect="allow",
        destination="http://127.0.0.1:8766/collect",
        body_fields=(("recipient", "owned"), ("amount", 98.7)),
    )
    policy = Policy(version=1, name="bill", rules=(rule,))
    assert (
        policy.evaluate(
            "post_message", PostArgs(url=rule.destination or "", body=body), sensitive_read=False
        ).effect
        == "allow"
    ) == allowed
    # Even a correct projection never bypasses sticky confidentiality.
    assert (
        policy.evaluate(
            "post_message",
            PostArgs(
                url=rule.destination or "", body=json.dumps({"recipient": "owned", "amount": 98.7})
            ),
            sensitive_read=True,
        ).effect
        == "deny"
    )
