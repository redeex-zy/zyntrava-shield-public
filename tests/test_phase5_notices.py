import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.lab.environment import receiver, seed_workspace
from zyntrava.models import ToolRequest
from zyntrava.notices import NOTICE, NoticeService
from zyntrava.policy import default_policy
from zyntrava.tools import LabTools


def build(tmp_path: Path, endpoint: str) -> Broker:
    workspace = tmp_path / "workspace"
    seed_workspace(workspace)
    return Broker(default_policy(endpoint), LabTools(workspace), AuditStore(tmp_path / "audit.db"))


def test_notice_is_constant_and_ordinary_sinks_stay_blocked(tmp_path: Path) -> None:
    with receiver() as (server, url):
        broker = build(tmp_path, url)
        session = broker.create_session()
        service = NoticeService(broker, tmp_path / "ledger.db")
        service.commit(broker, session, "public-request-1", url, time.time() + 0.01)
        broker.submit(
            session, ToolRequest(tool="read_file", arguments={"path": "sensitive/data.txt"})
        )
        denied = broker.submit(
            session,
            ToolRequest(
                tool="post_message", arguments={"url": url, "body": "model sanitized prose"}
            ),
        )
        assert denied.status == "blocked"
        assert broker.final_answer(session, "opaque secret").status == "blocked"
        assert (
            broker.submit(session, ToolRequest(tool="operator_notice", arguments={})).status
            == "blocked"
        )
        time.sleep(0.02)
        assert service.dispatch_due()[0]["execution"] == "succeeded"
        assert server.received == [NOTICE.encode()]
        assert service.dispatch_due() == []
        # Persistent replay protection is independent of the agent session or restart.
        again = NoticeService(broker, tmp_path / "ledger.db")
        assert again.dispatch_due() == []
        with pytest.raises(sqlite3.IntegrityError):
            again.commit(broker, broker.create_session(), "public-request-1", url, time.time() + 1)


def test_notice_rejects_late_commit_and_unscoped_destination(tmp_path: Path) -> None:
    broker = build(tmp_path, "http://127.0.0.1:8766/collect")
    service = NoticeService(broker, tmp_path / "ledger.db")
    session = broker.create_session()
    broker.submit(session, ToolRequest(tool="read_file", arguments={"path": "public/hello.txt"}))
    with pytest.raises(ValueError, match="precede"):
        service.commit(broker, session, "late", "http://127.0.0.1:8766/collect", time.time() + 1)
    with pytest.raises(ValueError, match="permission"):
        service.commit(
            broker,
            broker.create_session(),
            "wrong",
            "http://127.0.0.1:8767/collect",
            time.time() + 1,
        )


def test_concurrent_claims_have_one_attempt_even_without_agent_processing(tmp_path: Path) -> None:
    with receiver() as (server, url):
        broker = build(tmp_path, url)
        ledger = tmp_path / "ledger.db"
        service = NoticeService(broker, ledger)
        service.commit(broker, broker.create_session(), "silent-agent", url, time.time() + 0.01)
        time.sleep(0.02)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: NoticeService(broker, ledger).dispatch_due(), range(8)))
        assert server.received == [NOTICE.encode()]


def test_pre_effect_audit_failure_consumes_notice_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with receiver() as (server, url):
        broker = build(tmp_path, url)
        service = NoticeService(broker, tmp_path / "ledger.db")
        service.commit(broker, broker.create_session(), "audit-failure", url, time.time() + 0.01)
        time.sleep(0.02)

        def fail(**kwargs: object) -> str:
            raise OSError("synthetic unavailable audit")

        monkeypatch.setattr(service.actor.audit, "append", fail)
        with pytest.raises(OSError):
            service.dispatch_due()
        assert server.received == []
        assert NoticeService(broker, tmp_path / "ledger.db").dispatch_due() == []


def test_failed_commit_audit_does_not_leave_dispatchable_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with receiver() as (server, url):
        broker = build(tmp_path, url)
        service = NoticeService(broker, tmp_path / "ledger.db")

        def fail(**kwargs: object) -> str:
            raise OSError("synthetic unavailable audit")

        monkeypatch.setattr(service.actor.audit, "append", fail)
        with pytest.raises(OSError):
            service.commit(
                broker, broker.create_session(), "not-committed", url, time.time() + 0.01
            )
        time.sleep(0.02)
        assert service.dispatch_due() == []
        assert server.received == []


def test_unknown_delivery_never_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with receiver() as (server, url):
        broker = build(tmp_path, url)
        service = NoticeService(broker, tmp_path / "ledger.db")
        service.commit(broker, broker.create_session(), "unknown", url, time.time() + 0.01)
        original = service.actor.audit.append

        def fail_execution(**fields: object) -> str:
            if fields.get("phase") == "execution":
                raise OSError("synthetic post-effect audit loss")
            return original(**fields)

        monkeypatch.setattr(service.actor.audit, "append", fail_execution)
        time.sleep(0.02)
        assert service.dispatch_due()[0]["execution"] == "unknown"
        assert NoticeService(broker, tmp_path / "ledger.db").dispatch_due() == []
        assert server.received == [NOTICE.encode()]
