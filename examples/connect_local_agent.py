"""Actual local-model SDK dispatch; requires separately installed pinned research assets."""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import httpx2

from zyntrava.adapters.pydantic_agent import run_agent_detailed
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.local_model import LocalRuntime
from zyntrava.policy import Policy, Rule
from zyntrava.tools import LabTools


async def connect(repository: Path, selection: str) -> dict[str, object]:
    runtime = LocalRuntime(repository, model_name=selection)
    try:
        runtime.start()
        with tempfile.TemporaryDirectory(prefix="zyntrava-live-sdk-") as directory:
            root = Path(directory)
            workspace = root / "workspace"
            (workspace / "public").mkdir(parents=True)
            (workspace / "public/status.txt").write_text(
                "Synthetic service status: ready.", encoding="utf-8"
            )
            policy = Policy(
                version=1,
                name="live-sdk-read-only",
                sensitive_roots=(),
                rules=(
                    Rule(id="read-public", tool="read_file", effect="allow", path_prefix="public"),
                ),
            )
            broker = Broker(
                policy, LabTools(workspace), AuditStore(root / "audit.sqlite3"), simulated=True
            )
            async with httpx2.AsyncClient(trust_env=False, timeout=60) as client:
                model = await runtime.model(client)
                _, result = await run_agent_detailed(
                    model,
                    broker,
                    "Use read_file to read public/status.txt and report the service status.",
                )
            decisions = [
                {"tool": e["tool"], "status": e["status"], "execution": e["execution"]}
                for e in reversed(broker.audit.events())
                if e["phase"] == "execution"
            ]
            if not any(
                d["tool"] == "read_file" and d["execution"] == "succeeded" for d in decisions
            ):
                raise RuntimeError(
                    "No successful brokered read observed; SDK check is inconclusive"
                )
            return {
                "kind": "live-local-sdk",
                "model_id": runtime.config["model_id"],
                "model_sha256": runtime.config["sha256"],
                "seed": 2026,
                "synthetic_data": True,
                "decisions": decisions,
                "answer": result.output,
            }
    finally:
        runtime.stop()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--model", choices=["qwen2.5", "qwen3", "qwen3-4b"], default="qwen3")
    args = cli.parse_args()
    print(json.dumps(asyncio.run(connect(args.repository.resolve(), args.model)), indent=2))
