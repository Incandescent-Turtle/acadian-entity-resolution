import json

import httpx
import pandas as pd
import pytest

from acadian_er.config import BackendConfig
from acadian_er.lib_staging.voisinage import indexer
from acadian_er.rq2 import (FakeBackend, LabelledPair, OllamaBackend, OpenAICompatBackend,
                            build_context, build_prompt, check_faithfulness, parse_response,
                            read_labels, verification_metrics, write_labels)


@pytest.fixture
def pair(population):
    index = indexer(population)
    a = next(p for p in population if p.parents and p.enfants)
    b = next(p for p in population if p.tree_id != a.tree_id and p.parents)
    return a, b, index


def test_context_k0_vs_k2(pair):
    a, b, index = pair
    k0, k2 = build_context(a, b, index, 0), build_context(a, b, index, 2)
    ids0, ids2 = {f.id for f in k0.facts}, {f.id for f in k2.facts}
    assert {"A.name", "B.name", "A.sex"} <= ids0 and ids0 < ids2
    assert all(i.count(".") <= 2 for i in ids0)            # own facts only at k=0
    assert any(i.startswith(("A.father", "A.mother", "A.parent")) for i in ids2)
    assert len(ids2) == len(k2.facts)                       # ids are unique
    system, user = build_prompt(k2)
    assert "[A.name]" in user and "insufficient" in system


@pytest.mark.parametrize("reply, verdict", [
    ('{"verdict": "match", "evidence": [{"id": "A.name", "value": "x"}]}', "match"),
    ('Sure!\n```json\n{"verdict": "Not Match", "evidence": []}\n```', "not_match"),
    ('{"verdict": "not enough information"}', "insufficient"),
    ('{"verdict": "maybe"}', "invalid"),
    ("no json here", "invalid"),
    ('{"rationale": "{nested}", "verdict": "same person", "evidence": ["[A.name]"]}', "match"),
])
def test_parse(reply, verdict):
    assert parse_response(reply).verdict == verdict


def test_faithfulness(pair):
    a, b, index = pair
    ctx = build_context(a, b, index, 2)
    good = [{"id": "A.name", "value": a.nom_complet}, {"id": "B.sex", "value": ""}]
    bad = [{"id": "A.name", "value": "Somebody Else"}, {"id": "A.godparent.name", "value": "x"}]
    f = check_faithfulness(good + bad, ctx)
    assert (f.n_cited, f.n_id_found, f.n_faithful) == (4, 3, 2) and not f.all_faithful
    assert {u["id"] for u in f.unsupported} == {"A.name", "A.godparent.name"}


def test_fake_backend_cites_real_facts(pair):
    a, _, index = pair
    ctx = build_context(a, a, index, 2)                  # a record against itself
    v = parse_response(FakeBackend().complete(*build_prompt(ctx)))
    assert v.verdict == "match" and check_faithfulness(v.evidence, ctx).all_faithful
    v = parse_response(FakeBackend(hallucinate=True).complete(*build_prompt(ctx)))
    assert not check_faithfulness(v.evidence, ctx).all_faithful


def test_http_backends_request_shape(monkeypatch):
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append((url, json, headers))
        body = ({"message": {"content": '{"verdict": "match"}'}} if "api/chat" in url
                else {"choices": [{"message": {"content": '{"verdict": "match"}'}}]})
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("MY_KEY", "secret")
    assert OllamaBackend(BackendConfig(kind="ollama", model="m", base_url="http://h:1")).complete("s", "u")
    oa = OpenAICompatBackend(BackendConfig(kind="openai_compat", model="m", base_url="http://h/v1",
                                           api_key_env="MY_KEY"))
    assert parse_response(oa.complete("s", "u")).verdict == "match"
    (u1, b1, _), (u2, b2, h2) = sent
    assert u1 == "http://h:1/api/chat" and b1["format"] == "json" and b1["options"]["temperature"] == 0
    assert u2 == "http://h/v1/chat/completions" and b2["seed"] == 0
    assert h2["Authorization"] == "Bearer secret"


def test_labels_roundtrip_and_validation(tmp_path):
    pairs = [LabelledPair("p1", 1, "I1", 2, "I9", "match", "rm"), LabelledPair("p2", 1, "I2", 3, "I4")]
    path = write_labels(pairs, tmp_path / "l.jsonl")
    assert read_labels(path) == pairs
    path.write_text(json.dumps({"pair_id": "x", "tree_a": 1, "id_a": "a", "tree_b": 2,
                                "id_b": "b", "label": "yes"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_labels(path)


def test_verification_metrics():
    rows = pd.DataFrame({
        "k": [0] * 5, "gold": ["match", "match", "not_match", "not_match", "unsure"],
        "verdict": ["match", "insufficient", "match", "not_match", "match"],
        "n_cited": [2, 0, 2, 2, 1], "n_faithful": [2, 0, 1, 2, 1]})
    m = verification_metrics(rows).iloc[0]
    assert m["n_pairs"] == 4 and m["precision"] == 0.5 and m["recall"] == 0.5
    assert m["decided_rate"] == 0.75 and m["citation_faithfulness"] == 5 / 6
