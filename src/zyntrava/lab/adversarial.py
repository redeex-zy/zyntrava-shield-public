"""A/B/C plus explicit release ablation, using actual local side effects."""

import base64
import hashlib
import json
import platform
import random
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.json_input import strict_json
from zyntrava.lab.adversarial_schema import AdversarialCorpus, Profile
from zyntrava.lab.benchmark import wilson
from zyntrava.lab.environment import SYNTHETIC_VALUE, receiver, seed_workspace
from zyntrava.lab.evaluation import ExecutionOracle, execution_metrics
from zyntrava.lab.resources import ResourceMeter
from zyntrava.lab.snapshot import snapshot
from zyntrava.models import CountArgs, FetchArgs, ToolRequest
from zyntrava.paths import safe_path
from zyntrava.policy import Policy, default_policy
from zyntrava.tools import ACTION_ERRORS, LabTools, parse_action


def experiment_policy(endpoint: str, profile: Profile, *, release: bool) -> Policy:
    raw = json.loads(
        default_policy(endpoint, page=endpoint.replace("/collect", "/page")).model_dump_json()
    )
    if profile in {"read_only", "no_send_permission"}:
        raw["rules"] = [r for r in raw["rules"] if r["tool"] not in {"post_message", "write_file"}]
    if profile in {"deny_public", "deny_sensitive"}:
        raw["rules"].append(
            {
                "id": "profile-deny",
                "tool": "read_file",
                "effect": "deny",
                "path_prefix": "public" if profile == "deny_public" else "sensitive",
            }
        )
    if profile == "deny_network":
        raw["rules"].append(
            {
                "id": "profile-deny-send",
                "tool": "post_message",
                "effect": "deny",
                "destination": endpoint,
            }
        )
    if profile == "report_auto":
        for rule in raw["rules"]:
            if rule["tool"] == "write_file":
                rule["effect"] = "allow"
    if release and profile == "release_approved":
        raw["release_rules"] = [
            {
                "id": "approved-count",
                "source": "sensitive/records.json",
                "destination": endpoint,
                "max_records": 8,
            }
        ]
    return Policy.model_validate_json(json.dumps(raw))


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [a for r in rows for a in r["actions"] if a["unauthorized"]]
    good = [
        a
        for r in rows
        for a in r["actions"]
        if not a["unauthorized"] and a["expected"] == "succeeded"
    ]
    attacks = [r for r in rows if r["task_type"] == "malicious"]
    benign = [r for r in rows if r["task_type"] == "benign"]
    times = [a["elapsed_ms"] for r in rows for a in r["actions"]]
    completion = sum(all(a["executed"] for a in r["actions"]) for r in benign)
    return {
        "scenarios": len(rows),
        "attack_scenarios": len(attacks),
        "benign_scenarios": len(benign),
        "ambiguous_scenarios": sum(r["task_type"] == "ambiguous" for r in rows),
        "unauthorized_actions": len(bad),
        "unauthorized_actions_executed": sum(a["executed"] for a in bad),
        "attack_success_rate": sum(r["attack_succeeded"] for r in attacks) / len(attacks)
        if attacks
        else None,
        "legitimate_task_completion": completion / len(benign) if benign else None,
        "enforcement_false_negative_rate": sum(a["executed"] for a in bad) / len(bad)
        if bad
        else None,
        "enforcement_false_positive_rate": sum(not a["executed"] for a in good) / len(good)
        if good
        else None,
        "contract_match_rate": sum(a["matches_expectation"] for r in rows for a in r["actions"])
        / sum(len(r["actions"]) for r in rows),
        "median_action_ms": statistics.median(times),
        "p95_action_ms": sorted(times)[max(0, int(len(times) * 0.95) - 1)],
        "detection_precision": None,
        "detection_recall": None,
        "detection_metric_reason": "No independent malicious-text classification labels.",
    }


def run_adversarial(corpus_path: Path, output: Path, *, repeats: int = 3, seed: int = 3100) -> Path:
    if not 1 <= repeats <= 10 or corpus_path.stat().st_size > 5_000_000:
        raise ValueError("experiment budget exceeded")
    corpus = AdversarialCorpus.model_validate_json(
        json.dumps(strict_json(corpus_path.read_bytes(), max_items=100_000))
    )
    run_id = f"trace-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{str(uuid4())[:8]}"
    frozen = snapshot(output, run_id, corpus_path)
    results = {}
    for arm in ("unprotected", "basic", "full", "full_release"):
        rows: list[dict[str, Any]] = []
        meter = ResourceMeter()
        try:
            for trial in range(repeats):
                scenarios = list(corpus.scenarios)
                random.Random(seed + trial).shuffle(scenarios)  # noqa: S311 # nosec B311
                with tempfile.TemporaryDirectory(prefix="zyntrava-v3-") as temporary:
                    base = Path(temporary)
                    with receiver() as (server, endpoint):
                        values = {
                            "$ENDPOINT": endpoint,
                            "$PAGE": endpoint.replace("/collect", "/page"),
                            "$SECRET": SYNTHETIC_VALUE,
                            "$BASE64": base64.b64encode(SYNTHETIC_VALUE.encode()).decode(),
                            "$HEX": SYNTHETIC_VALUE.encode().hex(),
                            "$HALF1": SYNTHETIC_VALUE[:12],
                            "$HALF2": SYNTHETIC_VALUE[12:],
                        }
                        for scenario in scenarios:
                            workspace = base / scenario.id
                            seed_workspace(workspace)
                            for name, text in scenario.fixtures.items():
                                path = workspace / name
                                path.parent.mkdir(parents=True, exist_ok=True)
                                path.write_text(text, encoding="utf-8")
                            tools = LabTools(workspace)
                            protected = {
                                p.relative_to(workspace).as_posix(): p.read_text(encoding="utf-8")
                                for directory in ("sensitive", "private")
                                for p in (workspace / directory).rglob("*")
                                if p.is_file()
                            }
                            # Include leaf canaries, not just complete JSON source documents.
                            records = workspace / "sensitive/records.json"
                            if records.exists():
                                try:
                                    doc = json.loads(records.read_text(encoding="utf-8"))
                                    protected.update(
                                        {
                                            f"record-{i}": entry["value"]
                                            for i, entry in enumerate(doc["records"])
                                            if isinstance(entry.get("value"), str)
                                        }
                                    )
                                except (ValueError, KeyError, TypeError, AttributeError):
                                    pass  # Invalid sources are still tracked as complete bytes.
                            oracle = ExecutionOracle(endpoint, scenario.profile, protected)
                            if scenario.category == "prompt-provenance":
                                # This frozen family explicitly supplies a classified prompt.
                                # Classification belongs to the reference fixture, not a verdict.
                                oracle.sensitive_observed = True
                                oracle.visible_sources.add("classified-prompt")
                                oracle.protected["classified-prompt"] = scenario.prompt
                            broker = Broker(
                                experiment_policy(
                                    endpoint, scenario.profile, release=arm == "full_release"
                                ),
                                tools,
                                AuditStore(base / (scenario.id + ".sqlite3")),
                                mode="basic" if arm == "basic" else "full",
                                simulated=True,
                            )
                            session = broker.create_session()
                            if arm != "unprotected":
                                broker.observe(session, scenario.prompt, "user")
                            actions: list[dict[str, Any]] = []
                            for attempt in scenario.steps:
                                arguments = {
                                    k: values.get(v, v) if isinstance(v, str) else v
                                    for k, v in attempt.arguments.items()
                                }
                                proposal = ToolRequest(tool=attempt.tool, arguments=arguments)
                                received = len(server.received)
                                started = time.perf_counter()
                                status, execution, reason = "allowed", "failed", []
                                observed_output = None
                                try:
                                    if arm == "unprotected":
                                        tool, args = parse_action(proposal)
                                        if isinstance(
                                            args, (FetchArgs, CountArgs)
                                        ) and args.url not in {
                                            endpoint,
                                            endpoint.replace("/collect", "/page"),
                                        }:
                                            raise ValueError(
                                                "lab traffic must target its owned receiver"
                                            )
                                        if isinstance(args, CountArgs):
                                            observed_output = tools.execute(
                                                tool, args, count_limit=8
                                            )
                                        else:
                                            observed_output = tools.execute(tool, args)
                                        execution = "succeeded"
                                    else:
                                        outcome = broker.submit(session, proposal)
                                        if outcome.approval_id and attempt.approve:
                                            outcome = broker.resolve(outcome.approval_id, True)
                                        status, execution = outcome.status, outcome.execution
                                        reason = [e.rule for e in outcome.decision.evidence]
                                        observed_output = outcome.output
                                except ACTION_ERRORS:
                                    pass
                                executed = execution == "succeeded"
                                receipts = server.received[received:]
                                if proposal.tool in {"post_message", "export_count"}:
                                    executed = bool(receipts)
                                elif proposal.tool == "write_file" and executed:
                                    path = safe_path(workspace, str(arguments["path"]))
                                    executed = (
                                        path.read_text(encoding="utf-8") == arguments["content"]
                                    )
                                actual = (
                                    "sent_for_approval"
                                    if status == "sent_for_approval"
                                    else ("blocked" if status == "blocked" else execution)
                                )
                                evaluation = oracle.observe(
                                    proposal.tool,
                                    arguments,
                                    legacy_forbidden=attempt.unauthorized,
                                    approved=attempt.approve,
                                    status=status,
                                    execution=execution,
                                    executed=executed,
                                    output=observed_output,
                                    receipts=receipts,
                                    file_effect=(
                                        safe_path(workspace, str(arguments["path"])).read_bytes()
                                        if proposal.tool == "write_file" and executed
                                        else None
                                    ),
                                )
                                actions.append(
                                    {
                                        "evaluation_v4": evaluation,
                                        "tool": proposal.tool,
                                        "expected": attempt.expected,
                                        "unauthorized": attempt.unauthorized,
                                        "status": status,
                                        "execution": execution,
                                        "executed": executed,
                                        "matches_expectation": actual == attempt.expected,
                                        "evidence_rules": reason,
                                        "receiver_receipts": len(receipts),
                                        "receiver_payload_sha256": [
                                            hashlib.sha256(p).hexdigest() for p in receipts
                                        ],
                                        "elapsed_ms": (time.perf_counter() - started) * 1000,
                                    }
                                )
                            rows.append(
                                {
                                    "scenario": scenario.id,
                                    "category": scenario.category,
                                    "split": scenario.split,
                                    "trial": trial,
                                    "task_type": scenario.task_type,
                                    "profile": scenario.profile,
                                    "document_format": scenario.document_format,
                                    "attack_succeeded": any(
                                        a["unauthorized"] and a["executed"] for a in actions
                                    ),
                                    "actions": actions,
                                }
                            )
        finally:
            resources = meter.finish()
        unique = [r for r in rows if r["split"] == "heldout" and r["trial"] == 0]
        attacks = [r for r in unique if r["task_type"] == "malicious"]
        benign = [r for r in unique if r["task_type"] == "benign"]
        results[arm] = {
            "execution_aware_splits": {
                s: execution_metrics([r for r in rows if r["split"] == s])
                for s in ("development", "heldout")
            },
            "splits": {
                s: metrics([r for r in rows if r["split"] == s]) for s in ("development", "heldout")
            },
            "resources": resources,
            "uncertainty": {
                "unit": "unique first-pass held-out workflow; correlated author-selected cases",
                "attack_success_ci95": wilson(
                    sum(r["attack_succeeded"] for r in attacks), len(attacks)
                ),
                "benign_completion_ci95": wilson(
                    sum(all(a["executed"] for a in r["actions"]) for r in benign), len(benign)
                ),
            },
            "raw_scenarios": rows,
        }
    path = output / (run_id + ".json")
    path.write_text(
        json.dumps(
            {
                "experiment_id": run_id,
                **{k: v for k, v in frozen.items() if k != "source_sha256"},
                "created_at": datetime.now(UTC).isoformat(),
                "kind": corpus.kind,
                "evaluation_methodologies": ["legacy-static-v3", "zyntrava-execution-aware-4.0"],
                "corpus_version": corpus.version,
                "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
                "repeats": repeats,
                "seed": seed,
                "environment": {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "source_sha256": frozen["source_sha256"],
                },
                "results": results,
                "limitations": [
                    "Developer-authored synthetic contracts, not independent or field validation.",
                    "Unprotected arm retains structural filesystem/network/projector validation.",
                    "Full release authorizes record cardinality; ordinary sinks remain denied.",
                    "Invalid documents can fail validation; repeats add no diversity.",
                    "Family correlation limits population interpretation of the intervals.",
                    "Eight post-release traces assume a source after a denied export in C/B.",
                    "Their static label violations are not demonstrated source-to-sink leaks.",
                    "Noncompletion includes unavailable release tasks, not just policy errors.",
                    "RSS/CPU include harness and retained prior arms; latency includes local I/O.",
                    "No external product arm; architectural comparison is documented separately.",
                ],
            },
            indent=2,
        )
    )
    return path
