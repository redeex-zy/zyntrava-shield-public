import json
from pathlib import Path

from zyntrava.lab.adversarial import run_adversarial
from zyntrava.lab.adversarial_schema import AdversarialCorpus

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_corpus_has_distinct_families_formats_and_splits():
    corpus = AdversarialCorpus.model_validate_json(
        (ROOT / "benchmarks/corpus-v3.json").read_bytes()
    )
    assert len(corpus.scenarios) == 335
    assert len({s.category for s in corpus.scenarios}) == 18
    assert len({s.document_format for s in corpus.scenarios}) == 6
    assert sum(s.split == "heldout" for s in corpus.scenarios) == 106


def test_release_ablation_uses_real_receipts_and_replayable_snapshot(tmp_path):
    corpus = json.loads((ROOT / "benchmarks/corpus-v3.json").read_text())
    corpus["scenarios"] = [
        s
        for s in corpus["scenarios"]
        if s["category"] in {"approved-aggregate", "post-release-raw-sink"}
    ][:24]
    small = tmp_path / "corpus-v3.json"
    small.write_text(json.dumps(corpus))
    path = run_adversarial(small, tmp_path / "results", repeats=1)
    result = json.loads(path.read_text())
    assert (path.parent / result["source_snapshot"]).is_file()
    assert all(
        not r["attack_succeeded"] for r in result["results"]["full_release"]["raw_scenarios"]
    )
    # Without the release grant, no source was read. The frozen trace nevertheless
    # injects transformed bytes into the next call. Preserve these label violations;
    # they are not observed source-to-sink leaks and must be qualified in the report.
    assert any(r["attack_succeeded"] for r in result["results"]["full"]["raw_scenarios"])
    approved = [
        r
        for r in result["results"]["full_release"]["raw_scenarios"]
        if r["category"] == "approved-aggregate"
    ]
    assert approved and all(r["actions"][-1]["receiver_receipts"] == 1 for r in approved)
    assert all(
        r["actions"][0]["receiver_receipts"] == 0
        for r in result["results"]["full"]["raw_scenarios"]
    )
