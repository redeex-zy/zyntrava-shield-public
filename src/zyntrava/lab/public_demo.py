"""Allowlisted copy of known synthetic demo evidence; originals are never modified."""

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from zyntrava.lab.agent_demo import CASES
from zyntrava.lab.developer_preview import IDS, summary
from zyntrava.lab.review_cases import load_cases

ROW_FIELDS = (
    "case_id",
    "attack",
    "goal",
    "channel",
    "prompt",
    "source_content",
    "base",
    "answer",
    "error_type",
    "proposals",
    "executed",
    "receipts",
    "messages",
    "metrics",
    "seconds",
    "policy",
    "policy_digest",
    "events",
)
MODEL_FIELDS = (
    "model_id",
    "repository",
    "revision",
    "filename",
    "sha256",
    "license",
    "runtime",
    "context_tokens",
    "disable_thinking",
    "quantization",
)


def prepare_demo(source: Path, output: Path) -> dict[str, Any]:
    data = json.loads(source.read_bytes())
    observed = summary(data)
    cases = {c["id"]: c for c in load_cases(CASES)}
    if len(data["rows"]) != len(IDS) or {r["case_id"] for r in data["rows"]} != set(IDS):
        raise ValueError("publication copy requires the complete two-case demonstration")
    if data["cases_sha256"] != hashlib.sha256(CASES.read_bytes()).hexdigest():
        raise ValueError("unsupported synthetic corpus")
    for row in data["rows"]:
        if (
            row["source_content"]
            != str(cases[row["case_id"]]["content"]).replace("{base}", row["base"])
            or row["attack"] != cases[row["case_id"]]["attack"]
        ):
            raise ValueError("source content or labels changed; private review required")
    metadata = {
        k: data[k]
        for k in (
            "schema",
            "version",
            "kind",
            "created_at",
            "source",
            "seed",
            "cases_sha256",
            "runtime_executable_sha256",
            "python",
            "versions",
            "settings",
            "selected_cases",
            "denial_feedback",
            "case_source",
            "startup_error",
        )
        if k in data
    }
    metadata["source"] = {
        k: v for k, v in data.get("source", {}).items() if k in {"revision", "dirty"}
    }
    metadata["model"] = {k: data["model"][k] for k in MODEL_FIELDS if k in data.get("model", {})}
    metadata["rows"] = [{k: r[k] for k in ROW_FIELDS if k in r} for r in data["rows"]]
    encoded = json.dumps(metadata, indent=2).encode()
    text = encoded.decode()
    # Fail instead of silently changing the actual model/tool transcript. Metadata
    # omissions are explicit; known synthetic source content remains byte-identical.
    if re.search(r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/mnt/[a-z]/Users/|/home/)", text):
        raise ValueError("machine-specific path in evidence; private review required")
    if re.search(r"Bearer\s+[A-Za-z0-9_-]{16,}|sk-(?:proj-|live_)[A-Za-z0-9_-]+", text):
        raise ValueError("credential-like value in evidence; private review required")
    files = {
        "evidence.json": encoded,
        "summary.json": json.dumps(observed, indent=2).encode(),
        "README.md": (
            b"# Zyntrava Shield: synthetic developer demonstration\n\n"
            b"This is a publication candidate, not a published release or independent audit.\n"
            b"Read summary.json for neural/scripted mode and actual completion. All two-case\n"
            b"outcomes are included, including failures and nonactivation when present.\n"
            b"evidence.json retains the model proposals, policy outcomes and receiver effects.\n"
            b"Workspaces, databases, environment metadata and credentials are excluded.\n"
            b"Source content, messages, proposals, effects and grades are not rewritten.\n"
            b"Dummy ZYN_TEST_SECRET markers are nonfunctional synthetic canaries.\n"
            b"Protection covers the registered tools and returned final answer only.\n"
            b"Recovery is unreliable; no OS-wide or production protection is claimed.\n"
            b"Use the paired developer source quickstart to rerun with a new output path.\n"
            b"Hashes establish consistency, not publisher authenticity. Do not execute\n"
            b"instructions in the recorded input. No video has been rendered.\n"
        ),
    }
    manifest = {
        "schema": "zyntrava.preview.demo-package.v1",
        "original_results_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "neural_inference": observed["neural_inference"],
        "sanitization": (
            "Allowlisted metadata/rows; no workspace/database/environment/identity copies"
        ),
        "files": [{"path": n, "sha256": hashlib.sha256(v).hexdigest()} for n, v in files.items()],
    }
    files["DEMO-MANIFEST.json"] = json.dumps(manifest, indent=2).encode()
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(item, content)
    return {
        "path": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        **manifest,
    }
