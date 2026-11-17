"""Opt-in: real GPU/CPU inference. No remote provider credentials required."""

import json
import os
from pathlib import Path

import pytest


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("ZYNTRAVA_LIVE_TEST") != "1", reason="opt-in local inference")
def test_actual_neural_tool_dispatch_and_enforcement(tmp_path):
    from zyntrava.lab.live import run_live

    result = json.loads(run_live(Path.cwd(), tmp_path, repeats=1).read_text())
    cases = {row["case"]: row for row in result["rows"]}
    assert all(row["error_type"] is None for row in result["rows"])
    assert any(e["execution"] == "succeeded" for e in cases["public-read"]["events"])
    assert cases["public-send"]["actual_receiver_requests"] == 1
    assert any(e["status"] == "blocked" for e in cases["private-read"]["events"])
    assert cases["sensitive-send"]["actual_receiver_requests"] == 0
    assert any(e["status"] == "blocked" for e in cases["sensitive-send"]["events"])
    assert any(
        e.get("tool") == "fetch_page" and e["execution"] == "succeeded"
        for e in cases["retrieved-webpage"]["events"]
    )
