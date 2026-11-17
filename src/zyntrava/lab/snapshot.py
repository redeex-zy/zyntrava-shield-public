"""Freeze reviewed source before an experiment, excluding runtime state and secrets."""

import hashlib
import shutil
import subprocess  # nosec B404 -- fixed local Git metadata only.
import zipfile
from pathlib import Path
from typing import Any


def snapshot(output: Path, run_id: str, corpus_path: Path) -> dict[str, Any]:
    source = Path(__file__).resolve().parents[1]
    root = source.parents[1]
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{run_id}-source.zip"
    paths = list(source.rglob("*.py"))
    for name in (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "LICENSE",
        "NOTICE",
        "scripts/hatch_build.py",
        "scripts/evaluate-transfer.py",
        "scripts/isolation-poc.py",
        "scripts/compare-enforcement.py",
        "scripts/mcp-lab-server.py",
    ):
        if (root / name).is_file():
            paths.append(root / name)
    for directory in (
        "benchmarks/external/agentdojo",
        "benchmarks/comparator-configs",
        "benchmarks/external/agentdojo-original",
        "benchmarks/recovery-v1",
        "benchmarks/external/phase7-env",
        "benchmarks/external/phase7-agentdojo",
    ):
        paths.extend(p for p in (root / directory).glob("*") if p.is_file())
    for directory in ("benchmarks", "models", "apps/dashboard/out"):
        paths.extend(
            p
            for p in (
                (root / directory).iterdir()
                if directory == "benchmarks"
                else (root / directory).rglob("*")
            )
            if p.is_file()
            and (directory != "benchmarks" or p.parent == root / directory)
            and p.suffix in {".json", ".html", ".txt", ".js", ".css", ".svg", ".ico"}
        )
    paths.extend((root / "scripts").glob("*.py"))
    if (root / "docs/research/phase5-protocol.md").is_file():
        paths.append(root / "docs/research/phase5-protocol.md")
    if (root / "docs/research/phase6-protocol.md").is_file():
        paths.append(root / "docs/research/phase6-protocol.md")
    if (root / "docs/research/phase6-followup-protocol.md").is_file():
        paths.append(root / "docs/research/phase6-followup-protocol.md")
    if (root / "docs/research/phase7-protocol.md").is_file():
        paths.append(root / "docs/research/phase7-protocol.md")
    for name in ("phase7-method-correction.md", "phase7-pdf-followup.md"):
        if (root / "docs/research" / name).is_file():
            paths.append(root / "docs/research" / name)
    digest = hashlib.sha256()
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(set(paths)):
            relative = path.relative_to(root).as_posix()
            if relative == "benchmarks/" + corpus_path.name:
                continue
            content = path.read_bytes()
            if path.is_relative_to(source):
                digest.update(path.relative_to(source).as_posix().encode())
                digest.update(content)
            bundle.writestr(relative, content)
        bundle.writestr("benchmarks/" + corpus_path.name, corpus_path.read_bytes())
    return {
        "source_revision": subprocess.check_output(  # noqa: S603 # nosec B603
            [str(shutil.which("git")), "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            timeout=10,
        ).strip()
        if (root / ".git").is_dir() and shutil.which("git")
        else None,
        "source_snapshot": target.name,
        "source_snapshot_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_snapshot_packaging_complete": (root / "pyproject.toml").is_file(),
        "source_sha256": digest.hexdigest(),
    }
