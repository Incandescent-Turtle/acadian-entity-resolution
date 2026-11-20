"""End-to-end smoke tests on tiny synthetic data (CPU, fake LLM)."""

import pandas as pd

from genealogie_acadienne.donnees.instantane import lire_instantane

from acadian_er.cli import main
from acadian_er.experiments.rq1 import run_rq1
from acadian_er.experiments.rq2 import stage_candidates, stage_verify, synthetic_labelled_pairs


def test_rq1_end_to_end(tiny_cfg):
    summary = run_rq1(tiny_cfg, log=lambda *a: None)
    methods = set(tiny_cfg.rq1.methods)
    assert set(summary["method"]) == methods
    assert set(summary["tier"]) == set(tiny_cfg.benchmark.tiers) | {"all"}
    for col in ("recall@5", "recall@10", "mrr", "candidate_recall"):
        assert summary[col].between(0, 1).all()
    out = tiny_cfg.run_dir / "rq1"
    for f in ("summary.csv", "per_query.csv", "report.md", "config.yaml", "manifest.json"):
        assert (out / f).exists()
    assert all((out / "checkpoints" / f"rgcn_k{k}.pt").exists() for k in tiny_cfg.train.ks)
    # an unperturbed clone is easy: the old method finds it at the top almost always
    clean = summary.set_index(["method", "tier"]).loc[("exact_name", "t0_clean")]
    assert clean["recall@5"] >= 0.9


def test_rq2_end_to_end_with_fake_llm(tiny_cfg):
    people, pairs = synthetic_labelled_pairs(tiny_cfg, n=20)
    assert {p.label for p in pairs} == {"match", "not_match"}
    summary = stage_verify(tiny_cfg, people=people, pairs=pairs, log=lambda *a: None)
    assert list(summary["k"]) == [0, 2]
    assert (summary["citation_faithfulness"].dropna() == 1.0).all()   # fake cites real facts
    responses = pd.read_json(tiny_cfg.run_dir / "rq2" / "responses.jsonl", lines=True)
    assert len(responses) == 2 * len(pairs)


def test_rq2_candidate_export(tiny_cfg):
    pairs = stage_candidates(tiny_cfg, log=lambda *a: None)
    assert pairs and all(p.label is None for p in pairs)
    assert len({(p.a, p.b) for p in pairs}) == len(pairs)


def test_cli_synth(tmp_path, capsys):
    out = tmp_path / "snap"
    main(["synth", "--config", "configs/tiny_test.yaml", "--out", str(out)])
    assert lire_instantane(out) and "synthetic people written" in capsys.readouterr().out
