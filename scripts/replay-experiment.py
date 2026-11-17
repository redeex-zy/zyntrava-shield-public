"""Replay a trusted project-generated source archive without changing old results."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
cli = argparse.ArgumentParser()
cli.add_argument("experiment", type=Path)
cli.add_argument("--report", type=Path, default=None, help="New report path; never overwritten")
args = cli.parse_args()
original = args.experiment.resolve()
if not original.is_relative_to(root / "benchmarks/results"):
    cli.error("use a reviewed project-generated experiment under benchmarks/results")
data = json.loads(original.read_text())
archive = original.parent / data["source_snapshot"]
if not archive.resolve().is_relative_to(original.parent):
    raise ValueError("invalid source archive path")
if hashlib.sha256(archive.read_bytes()).hexdigest() != data["source_snapshot_sha256"]:
    raise ValueError("source snapshot checksum mismatch")
target = root / ".state" / f"replay-{str(uuid4())[:8]}"
target.mkdir(parents=True)
with zipfile.ZipFile(archive) as bundle:
    for member in bundle.infolist():
        if not (target / member.filename).resolve().is_relative_to(target):
            raise ValueError("archive path escape")
        if member.external_attr >> 16 & 0o170000 == 0o120000:
            raise ValueError("archive symlink rejected")
    bundle.extractall(target)
uv = root / (".bootstrap/Scripts/uv.exe" if os.name == "nt" else ".tools/linux-uv/bin/uv")
# Use a standard venv from the invoking approved Python, rather than a redirector
# that this Windows host's application-control policy may reject.
subprocess.run(  # noqa: S603 -- invoking trusted interpreter, fresh disposable environment.
    [sys._base_executable, "-m", "venv", str(target / ".venv")], check=True, timeout=60
)
subprocess.run([str(uv), "sync", "--locked"], cwd=target, check=True, timeout=180)  # noqa: S603
python = target / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
versions = {"zyntrava-traces-1": "1", "zyntrava-traces-2": "2", "zyntrava-adversarial-3": "3"}
version = versions[data["corpus_version"]]
subprocess.run(  # noqa: S603 -- fixed project replay command, no shell.
    [
        str(python),
        "-m",
        "zyntrava",
        "adversarial" if version == "3" else "benchmark",
        "--corpus",
        f"benchmarks/corpus-v{version}.json",
        "--repeats",
        "1",
        "--seed",
        str(data["seed"]),
        "--output",
        "replay-results",
    ],
    cwd=target,
    check=True,
    timeout=240,
)
replay = json.loads(next((target / "replay-results").glob("*.json")).read_text())


def outcomes(payload):
    return {
        mode: {
            r["scenario"]: {
                "attack": r["attack_succeeded"],
                "actions": [
                    {
                        k: a[k]
                        for k in (
                            "tool",
                            "unauthorized",
                            "status",
                            "execution",
                            "executed",
                            "receiver_receipts",
                        )
                    }
                    for a in r["actions"]
                ],
            }
            for r in result["raw_scenarios"]
            if r.get("repeat", r.get("trial")) == 0
        }
        for mode, result in payload["results"].items()
    }


matched = outcomes(data) == outcomes(replay)
report = {
    "original": original.name,
    "replay": replay["experiment_id"],
    "outcomes_match": matched,
    "workspace": str(target.relative_to(root)),
    "scope": "first-pass action effects across all recorded arms",
    "source_snapshot_sha256": data["source_snapshot_sha256"],
}
report_path = args.report or root / "artifacts" / f"replay-{uuid4().hex[:8]}.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
with report_path.open("x", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
if not matched:
    raise ValueError("replay outcomes differ")
print("PASS: source archive installed cleanly and action outcomes reproduced")
