"""Runnable, offline SDK example. Scripted tool decisions, real framework and file I/O."""

import json
import tempfile
from pathlib import Path
from typing import Any

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from zyntrava.adapters.pydantic_agent import run_agent
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.policy import Policy, Rule
from zyntrava.tools import LabTools


def demo() -> str:
    """Read a public file, deny a private read, then complete another authorized read."""
    with tempfile.TemporaryDirectory(prefix="zyntrava-sdk-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        for folder in ("public", "private"):
            (workspace / folder).mkdir(parents=True)
        (workspace / "public/status.txt").write_text(
            "Synthetic service status: ready.", encoding="utf-8"
        )
        (workspace / "private/record.txt").write_text(
            "Synthetic private fixture.", encoding="utf-8"
        )
        policy = Policy(
            version=1,
            name="sdk-read-only",
            sensitive_roots=(),
            rules=(Rule(id="read-public", tool="read_file", effect="allow", path_prefix="public"),),
        )
        broker = Broker(
            policy, LabTools(workspace), AuditStore(root / "audit.sqlite3"), simulated=True
        )
        paths = iter(["public/status.txt", "private/record.txt", "public/status.txt"])

        def scripted(messages: Any, info: AgentInfo) -> ModelResponse:
            path = next(paths, None)
            if path is None:
                return ModelResponse(parts=[TextPart("Scripted SDK task finished.")])
            return ModelResponse(parts=[ToolCallPart("read_file", {"path": path})])

        answer = run_agent(FunctionModel(scripted), broker, "Run the synthetic SDK sequence.")
        decisions = [e for e in reversed(broker.audit.events()) if e["phase"] == "decision"]
        summary = [{"tool": e["tool"], "status": e["status"]} for e in decisions]
        return json.dumps(
            {
                "kind": "scripted-framework-demo",
                "neural_inference": False,
                "decisions": summary,
                "final_answer": answer,
            },
            indent=2,
        )
