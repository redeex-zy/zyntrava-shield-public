import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from zyntrava.lab.developer_preview import run_preview
from zyntrava.lab.public_demo import prepare_demo


@pytest.fixture
def run(tmp_path):
    return run_preview(Path(__file__).resolve().parents[1], tmp_path / "exercise")


def test_publication_copy_preserves_effects_and_original_bytes_excludes_state(run, tmp_path):
    original = run.read_bytes()
    target = tmp_path / "demo.zip"
    report = prepare_demo(run, target)
    assert run.read_bytes() == original and not report["neural_inference"]
    with zipfile.ZipFile(target) as bundle:
        assert set(bundle.namelist()) == {
            "evidence.json",
            "summary.json",
            "README.md",
            "DEMO-MANIFEST.json",
        }
        data = json.loads(bundle.read("evidence.json"))
        old = json.loads(original)
        for row, raw in zip(data["rows"], old["rows"], strict=True):
            for key in [
                "source_content",
                "messages",
                "proposals",
                "executed",
                "receipts",
                "metrics",
            ]:
                assert row[key] == raw[key]
        manifest = json.loads(bundle.read("DEMO-MANIFEST.json"))
        for item in manifest["files"]:
            assert hashlib.sha256(bundle.read(item["path"])).hexdigest() == item["sha256"]
    with pytest.raises(FileExistsError):
        prepare_demo(run, target)


@pytest.mark.parametrize("change", ["machine-path", "source", "receipt"])
def test_suspicious_or_altered_data_is_not_silently_published(run, tmp_path, change):
    data = json.loads(run.read_bytes())
    if change == "machine-path":
        data["rows"][0]["answer"] = "C:\\Users\\PRIVATE_USER\\document.txt"
    elif change == "source":
        data["rows"][0]["source_content"] = "a different document"
    else:
        data["rows"][0]["receipts"] = []
    other = tmp_path / "changed.json"
    other.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare_demo(other, tmp_path / "bad.zip")
    assert not (tmp_path / "bad.zip").exists()
