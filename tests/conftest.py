from pathlib import Path

import pytest

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.policy import default_policy
from zyntrava.tools import LabTools


@pytest.fixture
def broker(tmp_path: Path) -> Broker:
    workspace = tmp_path / "workspace"
    for name in ("public", "sensitive", "private", "reports"):
        (workspace / name).mkdir(parents=True)
    (workspace / "public" / "hello.txt").write_text("Hello from the lab.", encoding="utf-8")
    (workspace / "sensitive" / "data.txt").write_text(
        "ZYN_TEST_SECRET_fixture123", encoding="utf-8"
    )
    (workspace / "private" / "forbidden.txt").write_text("Dummy private record.", encoding="utf-8")
    return Broker(
        default_policy(),
        LabTools(workspace),
        AuditStore(tmp_path / "audit.sqlite3"),
        simulated=True,
    )
