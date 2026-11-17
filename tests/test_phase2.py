import json
from pathlib import Path

from zyntrava.broker import Broker
from zyntrava.lab.benchmark import wilson
from zyntrava.lab.environment import receiver
from zyntrava.lab.schema import Corpus
from zyntrava.models import ToolRequest
from zyntrava.policy import default_policy


def test_real_page_fetch_requires_explicit_scope_and_tracks_untrusted_source(broker: Broker):
    with receiver() as (_, endpoint):
        page = endpoint.replace("/collect", "/page")
        session = broker.create_session()
        proposed = ToolRequest(tool="fetch_page", arguments={"url": page})
        assert broker.submit(session, proposed).status == "blocked"
        broker.policy = default_policy(endpoint, page=page)
        result = broker.submit(session, proposed)
        assert result.execution == "succeeded" and "<article>" in result.output
        observations = [e for e in broker.audit.events() if e["phase"] == "observation"]
        assert observations[0]["source"] == "tool"
        assert observations[0]["evidence"][0]["category"] == "indirect_prompt_injection"


def test_expanded_corpus_is_versioned_and_has_disjoint_splits():
    path = Path(__file__).resolve().parents[1] / "benchmarks/corpus-v2.json"
    corpus = Corpus.model_validate_json(path.read_bytes())
    assert len(corpus.scenarios) == 120
    assert len({s.category for s in corpus.scenarios}) == 20
    assert sum(s.split == "heldout" for s in corpus.scenarios) == 60
    assert {s.id for s in corpus.scenarios if s.split == "development"}.isdisjoint(
        s.id for s in corpus.scenarios if s.split == "heldout"
    )
    assert json.loads(path.read_text())["version"] == "zyntrava-traces-2"


def test_uncertainty_does_not_turn_zero_observed_failures_into_certainty():
    interval = wilson(0, 42)
    assert interval[0] == 0 and 0.08 < interval[1] < 0.09
