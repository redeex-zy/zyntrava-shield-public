"""Reproducible authorization experiments with actual synthetic side effects."""

import base64
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import statistics
import tempfile
import time
import tracemalloc
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.lab.environment import SYNTHETIC_VALUE, receiver, seed_workspace
from zyntrava.lab.resources import ResourceMeter
from zyntrava.lab.schema import Corpus
from zyntrava.models import ToolRequest
from zyntrava.paths import safe_path
from zyntrava.policy import default_policy
from zyntrava.tools import ACTION_ERRORS, LabTools, parse_action


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [max(0.0, center - half), min(1.0, center + half)]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unauthorized = [a for row in rows for a in row["actions"] if a["unauthorized"]]
    authorized = [a for row in rows for a in row["actions"] if not a["unauthorized"]]
    attacks = [row for row in rows if row["malicious"]]
    benign = [row for row in rows if not row["malicious"]]
    benign_no_sensitive_egress = [row for row in benign if not row["requires_sensitive_egress"]]
    times = [a["elapsed_ms"] for row in rows for a in row["actions"]]
    executed_bad = sum(a["executed"] for a in unauthorized)
    stopped_good = sum(not a["executed"] for a in authorized)
    completed = sum(all(a["executed"] for a in row["actions"]) for row in benign)
    return {
        "scenarios": len(rows),
        "attack_scenarios": len(attacks),
        "benign_scenarios": len(benign),
        "unauthorized_actions": len(unauthorized),
        "unauthorized_actions_executed": executed_bad,
        "attack_success_rate": ratio(sum(row["attack_succeeded"] for row in attacks), len(attacks)),
        "unauthorized_action_execution_rate": ratio(executed_bad, len(unauthorized)),
        "enforcement_false_negative_rate": ratio(executed_bad, len(unauthorized)),
        "enforcement_false_positive_rate": ratio(stopped_good, len(authorized)),
        "legitimate_task_completion": ratio(completed, len(benign)),
        "benign_without_sensitive_egress_completion": ratio(
            sum(all(a["executed"] for a in row["actions"]) for row in benign_no_sensitive_egress),
            len(benign_no_sensitive_egress),
        ),
        "detection_precision": None,
        "detection_recall": None,
        "detection_metric_reason": "No independent text-classification labels in this corpus.",
        "median_action_ms": statistics.median(times),
        "p95_action_ms": sorted(times)[max(0, int(len(times) * 0.95 + 0.999) - 1)],
    }


def run_benchmark(
    corpus_path: Path, output_dir: Path, *, seed: int = 2026, repeats: int = 3
) -> Path:
    if not 1 <= repeats <= 100:
        raise ValueError("repeats must be between 1 and 100")
    if corpus_path.stat().st_size > 1048576:
        raise ValueError("corpus exceeds 1 MiB")
    corpus_bytes = corpus_path.read_bytes()
    corpus = Corpus.model_validate_json(corpus_bytes).model_dump(mode="json")
    run_id = f"trace-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{str(uuid4())[:8]}"
    results: dict[str, Any] = {}
    for mode in ("unprotected", "basic", "full"):
        rows: list[dict[str, Any]] = []
        resources = ResourceMeter()
        tracemalloc.start()
        try:
            for repeat in range(repeats):
                scenarios = list(corpus["scenarios"])
                # Deterministic ordering only; authentication uses secrets, never this PRNG.
                random.Random(seed + repeat).shuffle(scenarios)  # noqa: S311 # nosec B311
                with tempfile.TemporaryDirectory(prefix="zyntrava-lab-") as temporary:
                    base = Path(temporary)
                    with receiver() as (server, endpoint):
                        replacements = {
                            "$ENDPOINT": endpoint,
                            "$PAGE": endpoint.replace("/collect", "/page"),
                            "$SECRET": SYNTHETIC_VALUE,
                            "$BASE64": base64.b64encode(SYNTHETIC_VALUE.encode()).decode(),
                            "$HEX": SYNTHETIC_VALUE.encode().hex(),
                            "$HALF1": SYNTHETIC_VALUE[:12],
                            "$HALF2": SYNTHETIC_VALUE[12:],
                        }
                        for scenario in scenarios:
                            root = base / scenario["id"]
                            seed_workspace(root)
                            tools = LabTools(root)
                            broker = Broker(
                                default_policy(endpoint, page=endpoint.replace("/collect", "/page"))
                                if corpus["version"] == "zyntrava-traces-2"
                                else default_policy(endpoint),
                                tools,
                                AuditStore(base / f"{scenario['id']}.sqlite3"),
                                mode="basic" if mode == "basic" else "full",
                                simulated=True,
                            )
                            session = broker.create_session()
                            if mode != "unprotected":
                                broker.observe(session, scenario.get("prompt", ""), "user")
                            actions = []
                            for step in scenario["steps"]:
                                args = {
                                    k: replacements.get(v, v) for k, v in step["arguments"].items()
                                }
                                proposal = ToolRequest(tool=step["tool"], arguments=args)
                                before_receipts = len(server.received)
                                started = time.perf_counter_ns()
                                status, execution, detected = "allowed", "failed", False
                                if mode == "unprotected":
                                    try:
                                        tool, parsed = parse_action(proposal)
                                        tools.execute(tool, parsed)
                                        execution = "succeeded"
                                    except ACTION_ERRORS:
                                        status = "unsupported_or_invalid"
                                else:
                                    outcome = broker.submit(session, proposal)
                                    if outcome.approval_id and step.get("approve", False):
                                        outcome = broker.resolve(outcome.approval_id, True)
                                    status, execution = outcome.status, outcome.execution
                                    detected = bool(outcome.decision.evidence)
                                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                                executed = execution == "succeeded"
                                if proposal.tool == "post_message":
                                    # Receiver-side evidence confirms the actual side effect.
                                    executed = len(server.received) > before_receipts
                                elif proposal.tool == "write_file":
                                    try:
                                        executed = safe_path(root, str(args["path"])).is_file()
                                    except ValueError:
                                        executed = False
                                actions.append(
                                    {
                                        "tool": proposal.tool,
                                        "unauthorized": step["unauthorized"],
                                        "status": status,
                                        "execution": execution,
                                        "executed": executed,
                                        "decision_evidence": detected,
                                        "elapsed_ms": elapsed_ms,
                                        "receiver_receipts": len(server.received) - before_receipts,
                                    }
                                )
                            seen_sensitive = False
                            sensitive_egress = False
                            for step in scenario["steps"]:
                                if step["tool"] == "read_file" and step["arguments"][
                                    "path"
                                ].startswith("sensitive/"):
                                    seen_sensitive = True
                                elif (
                                    step["tool"] in {"write_file", "post_message"}
                                    and seen_sensitive
                                ):
                                    sensitive_egress = True
                            rows.append(
                                {
                                    "scenario": scenario["id"],
                                    "category": scenario["category"],
                                    "split": scenario["split"],
                                    "repeat": repeat,
                                    "malicious": scenario["malicious"],
                                    "requires_sensitive_egress": sensitive_egress,
                                    "has_sensitive_read": any(
                                        s["tool"] == "read_file"
                                        and s["arguments"]["path"].startswith("sensitive/")
                                        for s in scenario["steps"]
                                    ),
                                    "attack_succeeded": any(
                                        a["unauthorized"] and a["executed"] for a in actions
                                    ),
                                    "actions": actions,
                                }
                            )
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
            resource_stats = resources.finish()
        unique_heldout = [r for r in rows if r["repeat"] == 0 and r["split"] == "heldout"]
        unique_attacks = [r for r in unique_heldout if r["malicious"]]
        unique_benign = [r for r in unique_heldout if not r["malicious"]]
        results[mode] = {
            "splits": {
                split: summarize([r for r in rows if r["split"] == split])
                for split in ("development", "heldout")
            },
            "peak_traced_python_bytes": peak,
            "process_peak_rss_bytes": resource_stats["sampled_peak_process_rss_bytes"],
            "resources": resource_stats,
            "uncertainty": {
                "unit": "unique held-out scenario; repeats excluded",
                "method": "95% Wilson intervals; assumes independent Bernoulli cases",
                "qualification": (
                    "Template families are correlated and author-selected; "
                    "not a population guarantee."
                ),
                "attack_success_ci95": wilson(
                    sum(r["attack_succeeded"] for r in unique_attacks), len(unique_attacks)
                ),
                "benign_completion_ci95": wilson(
                    sum(all(a["executed"] for a in r["actions"]) for r in unique_benign),
                    len(unique_benign),
                ),
            },
            "raw_scenarios": rows,
        }
    for split in ("development", "heldout"):
        baseline = results["unprotected"]["splits"][split]["median_action_ms"]
        for mode in ("basic", "full"):
            metrics = results[mode]["splits"][split]
            metrics["median_overhead_ms_vs_unprotected"] = metrics["median_action_ms"] - baseline
    source_root = Path(__file__).resolve().parents[1]
    source_hash = hashlib.sha256()
    for source_path in sorted(source_root.rglob("*.py")):
        source_hash.update(source_path.relative_to(source_root).as_posix().encode())
        source_hash.update(source_path.read_bytes())
    dependency_versions = {}
    for name in ("fastapi", "pydantic", "pydantic-ai-slim"):
        try:
            dependency_versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependency_versions[name] = "not installed"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{run_id}.json"
    snapshot = output_dir / f"{run_id}-source.zip"
    project_root = source_root.parents[1]
    with zipfile.ZipFile(snapshot, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source_path in sorted(source_root.rglob("*.py")):
            archive.write(
                source_path, "src/zyntrava/" + source_path.relative_to(source_root).as_posix()
            )
        metadata_names = ("pyproject.toml", "uv.lock", "README.md", "LICENSE", "NOTICE")
        metadata_included = []
        for name in metadata_names:
            path = project_root / name
            if path.is_file():
                archive.write(path, name)
                metadata_included.append(name)
        archive.writestr("benchmarks/" + corpus_path.name, corpus_bytes)
        # Keep wheel data and optional compiled UI available to archived-source installation.
        for name in ("corpus-v1.json", "corpus-v2.json", "corpus-v3.json"):
            extra = project_root / "benchmarks" / name
            if name != corpus_path.name and extra.is_file():
                archive.write(extra, "benchmarks/" + name)
        for relative in ("apps/dashboard/out", "models"):
            directory = project_root / relative
            for asset in sorted(directory.rglob("*")):
                if asset.is_file() and asset.suffix != ".gguf":
                    archive.write(asset, asset.relative_to(project_root).as_posix())
        build_hook = project_root / "scripts/hatch_build.py"
        if build_hook.is_file():
            archive.write(build_hook, "scripts/hatch_build.py")
    payload = {
        "experiment_id": run_id,
        "source_snapshot": snapshot.name,
        "source_snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "source_snapshot_packaging_complete": len(metadata_included) == len(metadata_names),
        "created_at": datetime.now(UTC).isoformat(),
        "kind": corpus["kind"],
        "corpus_version": corpus["version"],
        "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "seed": seed,
        "repeats": repeats,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependencies": dependency_versions,
            "source_sha256": source_hash.hexdigest(),
        },
        "limitations": [
            "Fixed trace replay; no LLM inference or attack generation.",
            "Held-out split authored by the implementer; no independent validation.",
            "Repeat runs are not independent samples and do not increase corpus diversity.",
            "Tracemalloc peak plus sampled runner RSS; includes harness and retained results.",
            "Includes cold starts, SQLite, tracemalloc and local I/O; not production latency.",
        ],
        "external_comparators": {"Pipelock": "not run", "Adrian": "not run", "CaMeL": "not run"},
        "results": results,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target
