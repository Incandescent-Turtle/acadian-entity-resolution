"""RQ1 stages: benchmark -> train (one encoder per k) -> rank with every method -> report.

Outputs (under `results/<config.name>/rq1/`):
  checkpoints/rgcn_k{k}.pt (+ .json loss history)
  summary.csv, per_query.csv, report.md, config.yaml, manifest.json
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from genealogie_acadienne.commun.voisinage import Cle, indexer

from ..baselines import EmbeddingRanker, ExactNameCriteriaRanker, SentenceTransformerEncoder, TfidfEncoder
from ..baselines.base import cosine_scores
from ..benchmark import Benchmark, build_benchmark, load_benchmark, save_benchmark
from ..config import Config, seed_everything
from ..data import load_population
from ..evaluation import rank_of_target, summarise, write_report
from ..evaluation.report import write_manifest
from ..graph import FamilyGraph, build_graph
from ..model.train import TrainedEncoder, embed, load_encoder, save_encoder, train_encoder


def rq1_dir(cfg: Config) -> Path:
    return cfg.run_dir / "rq1"


def stage_benchmark(cfg: Config, log=print) -> Benchmark:
    seed_everything(cfg.seed)
    bench = build_benchmark(load_population(cfg), cfg, log=log)
    save_benchmark(bench, cfg.benchmark.out_dir, cfg)
    log(f"benchmark written to {cfg.benchmark.out_dir}")
    return bench


def _training_graph(bench: Benchmark, cfg: Config) -> tuple[FamilyGraph, set[Cle]]:
    """Training uses the population WITHOUT clones; benchmark anchors are never anchors."""
    clone_trees = set(bench.clone_trees)
    population = [p for p in bench.people if p.tree_id not in clone_trees]
    return build_graph(population, cfg.features), set(bench.anchors)


def stage_train(cfg: Config, bench: Benchmark | None = None, log=print) -> dict[int, TrainedEncoder]:
    seed_everything(cfg.seed)
    bench = bench or load_benchmark(cfg.benchmark.out_dir)
    graph, exclude = _training_graph(bench, cfg)
    log(f"training graph: {graph.num_nodes} nodes, {graph.data.edge_index.shape[1]} edges")
    encoders = {}
    for k in cfg.train.ks:
        enc = train_encoder(graph, k, cfg, exclude=exclude, log=log)
        save_encoder(enc, rq1_dir(cfg) / "checkpoints" / f"rgcn_k{k}.pt", graph.encoder.dim)
        encoders[k] = enc
    return encoders


class RGCNRanker:
    def __init__(self, enc: TrainedEncoder, graph: FamilyGraph, keys: list[Cle], cfg: Config):
        self.name = f"rgcn_k{enc.k}"
        keys = sorted(set(keys))
        self.embeddings = dict(zip(keys, embed(enc, graph, keys, cfg)))

    def score(self, query: Cle, candidates: list[Cle]) -> np.ndarray:
        return cosine_scores(self.embeddings, query, candidates)


def make_ranker(method: str, cfg: Config, people: list, needed: list[Cle],
                encoders: dict[int, TrainedEncoder] | None = None, graph: FamilyGraph | None = None):
    """Build one ranker over `people` (index of everyone that may be scored).
    `needed`: every key that will appear as a query or candidate (embedded up front)."""
    index = indexer(people)
    if method == "exact_name":
        return ExactNameCriteriaRanker(index)
    if method == "tfidf":
        return EmbeddingRanker(TfidfEncoder(), index, needed)
    if method == "sentence_transformer":
        return EmbeddingRanker(SentenceTransformerEncoder(cfg.text_embedding), index, needed)
    if method.startswith("rgcn_k"):
        k = int(method.removeprefix("rgcn_k"))
        enc = (encoders or {}).get(k) or load_encoder(rq1_dir(cfg) / "checkpoints" / f"rgcn_k{k}.pt", cfg)
        return RGCNRanker(enc, graph or build_graph(people, cfg.features), needed, cfg)
    raise ValueError(f"unknown RQ1 method {method!r}")


def _make_rankers(cfg: Config, bench: Benchmark, encoders: dict[int, TrainedEncoder] | None, log):
    needed = sorted({q.query for q in bench.queries} | {c for q in bench.queries for c in q.candidates})
    graph = None
    if any(m.startswith("rgcn") for m in cfg.rq1.methods):
        graph = build_graph(bench.people, cfg.features)          # population + clones
    for method in cfg.rq1.methods:
        yield make_ranker(method, cfg, bench.people, needed, encoders, graph)
        log(f"  ranker ready: {method}")


def stage_evaluate(cfg: Config, bench: Benchmark | None = None,
                   encoders: dict[int, TrainedEncoder] | None = None, log=print) -> pd.DataFrame:
    seed_everything(cfg.seed)
    bench = bench or load_benchmark(cfg.benchmark.out_dir)
    rows = []
    for ranker in _make_rankers(cfg, bench, encoders, log):
        for q in bench.queries:
            scores = ranker.score(q.query, q.candidates)
            rows.append({"method": ranker.name, "tier": q.tier,
                         "query_tree": q.query[0], "query_id": q.query[1],
                         "target_tree": q.target[0], "target_id": q.target[1],
                         "n_candidates": len(q.candidates),
                         "rank": rank_of_target(scores, q.candidates, q.target, q.query, cfg.seed),
                         "perturbation": q.perturbation})
    per_query = pd.DataFrame(rows)
    per_query["rank"] = per_query["rank"].astype("Float64")
    summary = summarise(per_query, cfg.rq1.recall_ks)
    out = rq1_dir(cfg)
    write_manifest(cfg, out, stage="rq1", n_queries=len(bench.queries))
    path = write_report(summary, per_query, out, f"RQ1 retrieval — {cfg.name}")
    log(f"report written to {path}")
    return summary


def run_rq1(cfg: Config, log=print) -> pd.DataFrame:
    """All RQ1 stages in one go (used by `acadian-er rq1-all` and the smoke test)."""
    bench = stage_benchmark(cfg, log=log)
    encoders = stage_train(cfg, bench, log=log) if any(m.startswith("rgcn") for m in cfg.rq1.methods) else {}
    return stage_evaluate(cfg, bench, encoders, log=log)
