"""Verify included synthetic evidence bytes and regrade observed effects; no model runs."""

import hashlib
import json
from pathlib import Path

from zyntrava.lab.developer_preview import summary

root = Path(__file__).resolve().parents[1]
reports = []
for folder in sorted((root / "evidence").iterdir()):
    if not folder.is_dir():
        continue
    manifest = json.loads((folder / "DEMO-MANIFEST.json").read_bytes())
    for item in manifest["files"]:
        name = item["path"]
        if name not in {"evidence.json", "summary.json", "README.md"}:
            raise ValueError("Unexpected evidence member")
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Evidence checksum differs")
    data = json.loads((folder / "evidence.json").read_bytes())
    observed = summary(data)
    if observed != json.loads((folder / "summary.json").read_bytes()):
        raise ValueError("Execution-aware regrade differs from saved summary")
    reports.append({"evidence": folder.name, "hashes_match": True, "regrade_matches": True})
print(json.dumps(reports, indent=2))
