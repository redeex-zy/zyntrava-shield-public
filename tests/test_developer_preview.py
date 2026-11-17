import json
from copy import deepcopy
from pathlib import Path

import pytest

from zyntrava.lab.developer_preview import run_preview, summary


def test_no_gpu_exercise_uses_actual_broker_files_receiver_and_labels_scripted(tmp_path):
    output = tmp_path / "exercise"
    result = run_preview(Path(__file__).resolve().parents[1], output)
    data = json.loads(result.read_bytes())
    observed = summary(data)
    assert observed["neural_inference"] is False and observed["experimental_recovery"] is False
    clean, injected = observed["rows"]
    assert clean["legitimate_task_complete"] and not clean["activated"]
    assert injected["activated"] and injected["goal_rejected_before_execution"] == 1
    assert injected["legitimate_task_complete"] and injected["receiver_receipts"] == 1
    assert all(r["forbidden_effects"] == r["duplicate_effects"] == 0 for r in observed["rows"])
    row = data["rows"][1]
    assert row["proposals"][1]["outcome"]["execution"] == "not_run"
    assert all(e["arguments"].get("path") != "private/operator.txt" for e in row["executed"])
    tampered = deepcopy(data)
    tampered["rows"][1]["receipts"] = []
    with pytest.raises(ValueError, match="grade"):
        summary(tampered)
    with pytest.raises(FileExistsError):
        run_preview(Path(__file__).resolve().parents[1], output)


def test_invalid_ports_do_not_create_partial_output(tmp_path):
    with pytest.raises(ValueError):
        run_preview(tmp_path, tmp_path / "invalid", service_base_port=1)
    assert not (tmp_path / "invalid").exists()
