"""Finite single-operator synthetic pilot support. No remote or multi-user service."""

import os
import secrets
import socket
import sqlite3
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Any

import httpx
import uvicorn

from zyntrava.api import create_app
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker


class PilotAPI:
    def __init__(self, broker: Broker) -> None:
        self.broker = broker
        self.operator = secrets.token_urlsafe(32)
        self.agent = secrets.token_urlsafe(32)
        self.listener: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.server: uvicorn.Server | None = None
        self.url = ""

    def __enter__(self) -> "PilotAPI":
        try:
            self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == "nt":
                self.listener.setsockopt(socket.SOL_SOCKET, vars(socket)["SO_EXCLUSIVEADDRUSE"], 1)
            self.listener.bind(("127.0.0.1", 0))
            self.listener.listen(16)
            authority = f"127.0.0.1:{self.listener.getsockname()[1]}"
            self.url = f"http://{authority}"
            app = create_app(
                self.broker, admin_token=self.operator, agent_token=self.agent, authority=authority
            )
            self.server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    access_log=False,
                    log_level="error",
                    limit_concurrency=16,
                    timeout_keep_alive=2,
                    timeout_graceful_shutdown=3,
                )
            )
            self.thread = threading.Thread(
                target=self.server.run, kwargs={"sockets": [self.listener]}, daemon=True
            )
            self.thread.start()
            deadline = time.monotonic() + 10
            with httpx.Client(trust_env=False, timeout=0.5) as client:
                while time.monotonic() < deadline:
                    try:
                        response = client.get(
                            self.url + "/ready",
                            headers={"Authorization": f"Bearer {self.operator}"},
                        )
                        if response.status_code == 200:
                            return self
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.05)
            raise TimeoutError("local pilot readiness timeout")
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive() and self.server:
                self.server.force_exit = True
                self.thread.join(timeout=2)
            if self.thread.is_alive():
                raise RuntimeError("pilot API shutdown not verified")
        if self.listener:
            self.listener.close()

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def backup_audit(audit: AuditStore, destination: Path) -> dict[str, Any]:
    """SQLite-consistent snapshot. Does NOT restore sessions, credentials or approvals."""
    with destination.open("xb"):
        pass
    with audit.connect() as source, sqlite3.connect(destination) as target:
        source.backup(target)
    with sqlite3.connect(destination) as restored:
        integrity = restored.execute("PRAGMA integrity_check").fetchone()
        rows = restored.execute("SELECT count(*) FROM events").fetchone()
    if integrity != ("ok",):
        raise RuntimeError("backup integrity verification failed")
    return {"integrity": "ok", "event_rows": rows[0]}
