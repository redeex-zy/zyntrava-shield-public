import json
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from zyntrava.lab.benchmark import run_benchmark


def test_benchmark_uses_actual_local_side_effects_and_exposes_utility_cost(tmp_path: Path):
    corpus = Path(__file__).resolve().parents[1] / "benchmarks/corpus-v1.json"
    result = json.loads(run_benchmark(corpus, tmp_path, repeats=1).read_text())
    base, basic, full = (
        result["results"][m]["splits"]["heldout"] for m in ("unprotected", "basic", "full")
    )
    assert base["unauthorized_actions_executed"] > basic["unauthorized_actions_executed"] > 0
    assert full["unauthorized_actions_executed"] == 0
    assert full["legitimate_task_completion"] < basic["legitimate_task_completion"]
    assert full["enforcement_false_positive_rate"] > 0
    assert full["detection_recall"] is None
    assert result["external_comparators"]["Pipelock"] == "not run"
    assert result["source_snapshot_packaging_complete"] is True
    with zipfile.ZipFile(tmp_path / result["source_snapshot"]) as snapshot:
        assert {"README.md", "LICENSE", "NOTICE", "pyproject.toml", "uv.lock"} <= set(
            snapshot.namelist()
        )
    leaks = [r for r in result["results"]["full"]["raw_scenarios"] if r["malicious"]]
    assert sum(a["receiver_receipts"] for r in leaks for a in r["actions"]) == 0


def test_untrusted_corpus_identifier_cannot_escape_lab(tmp_path: Path):
    corpus = Path(__file__).resolve().parents[1] / "benchmarks/corpus-v1.json"
    payload = json.loads(corpus.read_text())
    payload["scenarios"][0]["id"] = "../../outside"
    unsafe = tmp_path / "unsafe.json"
    unsafe.write_text(json.dumps(payload))
    with pytest.raises(ValidationError):
        run_benchmark(unsafe, tmp_path / "results", repeats=1)
    assert not (tmp_path / "results").exists()
