import pytest
from fastapi.testclient import TestClient

from zyntrava.api import create_app
from zyntrava.broker import Broker

ADMIN = "operator-fixture-credential-00000000000"
AGENT = "agent-fixture-credential-0000000000000"


@pytest.fixture
def client(broker: Broker):
    return TestClient(
        create_app(broker, admin_token=ADMIN, agent_token=AGENT, authority="testserver")
    )


def auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_admin_role_cannot_be_used_by_agent(client):
    assert client.get("/overview").status_code == 401
    assert client.get("/overview", headers=auth(AGENT)).status_code == 403
    assert client.get("/overview", headers=auth(ADMIN)).json()["evaluated_actions"] == 0


def test_end_to_end_api_action_approval_and_audit(client, broker: Broker):
    session = client.post("/sessions", json={}, headers=auth(AGENT)).json()["session_id"]
    response = client.post(
        f"/sessions/{session}/actions",
        headers=auth(AGENT),
        json={"tool": "write_file", "arguments": {"path": "reports/api.txt", "content": "safe"}},
    )
    assert response.status_code == 200
    pending = response.json()
    assert pending["status"] == "sent_for_approval"
    url = f"/approvals/{pending['approval_id']}"
    assert client.post(url, json={"allow": True}, headers=auth(AGENT)).status_code == 403
    assert not (broker.tools.root / "reports/api.txt").exists()
    result = client.post(url, json={"allow": True}, headers=auth(ADMIN)).json()
    assert result["execution"] == "succeeded"
    assert (broker.tools.root / "reports/api.txt").read_text() == "safe"
    assert client.get("/events", headers=auth(ADMIN)).json()
    assert client.get("/overview", headers=auth(ADMIN)).json()["pending_approvals"] == 0


def test_origin_dns_rebinding_and_cookie_only_requests_rejected(client):
    assert client.get("/health", headers={"Host": "attacker.invalid"}).status_code == 403
    assert (
        client.post(
            "/sessions", json={}, headers={**auth(ADMIN), "Origin": "https://attacker.invalid"}
        ).status_code
        == 403
    )
    assert (
        client.post("/sessions", json={}, headers={"Cookie": f"token={ADMIN}"}).status_code == 401
    )
    assert client.post("/sessions", content="", headers=auth(ADMIN)).status_code == 415


def test_validation_response_does_not_echo_sensitive_value(client):
    secret = "ZYN_TEST_SECRET_do_not_echo"
    response = client.post(
        "/sessions/unknown/actions",
        json={"tool": "x", "arguments": {}, "secret": secret},
        headers=auth(AGENT),
    )
    assert response.status_code == 422 and secret not in response.text


def test_oversized_body_and_security_headers(client):
    result = client.post(
        "/sessions/unknown/actions",
        content='{"large":"' + "x" * 70000 + '"}',
        headers={**auth(AGENT), "Content-Type": "application/json"},
    )
    assert result.status_code == 413
    assert client.get("/health").headers["cache-control"] == "no-store"
