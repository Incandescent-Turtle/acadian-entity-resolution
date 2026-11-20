"""RQ2 stages.

  stage_candidates  propose pairs to hand-label: sample real people, rank their
                    relaxed-name candidates with an RQ1 method, export the top-n
                    pairs (label = null) to `rq2.candidates_out`.
  stage_verify      for every labelled pair and every k in `rq2.ks`: build the
                    context, prompt the backend, parse, check faithfulness.
                    Writes results/<name>/rq2/{responses.jsonl, summary.csv, report.md}.

`synthetic_labelled_pairs` builds labelled pairs from the synthetic generator's
ground truth, for development and tests only (never mixed with real labels).
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pandas as pd

from genealogie_acadienne import Personne

from ..config import Config, seed_everything
from ..data import load_population
from ..evaluation.report import markdown_table, write_manifest
from ..lib_staging.candidats import IndexCandidats
from ..lib_staging.synthetique import generer_population
from ..lib_staging.voisinage import Cle, indexer
from ..rq2 import (LabelledPair, build_context, build_prompt, check_faithfulness, make_backend,
                   parse_response, read_labels, verification_metrics, write_labels)
from ..rq2.backends import LLMBackend
from .rq1 import make_ranker


def rq2_dir(cfg: Config) -> Path:
    return cfg.run_dir / "rq2"


def _ordered(a: Cle, b: Cle) -> tuple[Cle, Cle]:
    return (a, b) if a <= b else (b, a)


def stage_candidates(cfg: Config, log=print) -> list[LabelledPair]:
    seed_everything(cfg.seed)
    rc = cfg.rq2
    people = load_population(cfg)
    index = IndexCandidats(people)
    rng = random.Random(cfg.seed)
    queries = rng.sample(sorted(index.personnes), min(rc.n_queries, len(index.personnes)))
    cands = {q: index.candidats(index.personnes[q]) for q in queries}
    cands = {q: c for q, c in cands.items() if c}
    needed = sorted(set(cands) | {c for cs in cands.values() for c in cs})
    ranker = make_ranker(rc.candidate_method, cfg, people, needed)
    seen, pairs = set(), []
    for q, cs in cands.items():
        scores = ranker.score(q, cs)
        for _, c in sorted(zip(scores.tolist(), cs), key=lambda t: (-t[0], t[1]))[: rc.top_n]:
            a, b = _ordered(q, c)
            if (a, b) in seen:
                continue
            seen.add((a, b))
            pairs.append(LabelledPair(f"p{len(pairs) + 1:04d}", a[0], a[1], b[0], b[1],
                                      source=f"{rc.candidate_method} top-{rc.top_n}"))
    write_labels(pairs, rc.candidates_out)
    log(f"{len(pairs)} candidate pairs written to {rc.candidates_out} (fill in `label`)")
    return pairs


def synthetic_labelled_pairs(cfg: Config, n: int) -> tuple[list[Personne], list[LabelledPair]]:
    """Synthetic people + labelled pairs (half true duplicates across trees,
    half hard negatives from the same relaxed-name candidate lists)."""
    s = cfg.data.synthetic
    pop = generer_population(cfg.seed, s.n_fondateurs, s.n_generations, s.n_arbres, s.profondeur_arbre)
    rng = random.Random(cfg.seed)
    by_true: dict[int, list[Cle]] = {}
    for k, t in sorted(pop.identites.items()):
        by_true.setdefault(t, []).append(k)
    positives = [_ordered(ks[0], ks[1]) for ks in by_true.values()
                 if len(ks) > 1 and ks[0][0] != ks[1][0]]
    index = IndexCandidats(pop.personnes)
    negatives = []
    for a, _ in positives:
        others = [c for c in index.candidats(index.personnes[a])
                  if pop.identites[c] != pop.identites[a]]
        if others:
            negatives.append(_ordered(a, rng.choice(others)))
    rng.shuffle(positives)
    rng.shuffle(negatives)
    half = n // 2
    chosen = [(p, "match") for p in positives[:half]] + [(p, "not_match") for p in negatives[: n - half]]
    pairs = [LabelledPair(f"s{i + 1:04d}", a[0], a[1], b[0], b[1], label=label, source="synthetic")
             for i, ((a, b), label) in enumerate(chosen)]
    return pop.personnes, pairs


def stage_verify(cfg: Config, people: list[Personne] | None = None,
                 pairs: list[LabelledPair] | None = None, backend: LLMBackend | None = None,
                 log=print) -> pd.DataFrame:
    seed_everything(cfg.seed)
    rc = cfg.rq2
    people = people if people is not None else load_population(cfg)
    pairs = pairs if pairs is not None else read_labels(rc.labels_path)
    pairs = [p for p in pairs if p.label is not None][: rc.max_pairs]
    backend = backend or make_backend(rc.backend)
    index = indexer(people)
    out = rq2_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(out / "responses.jsonl", "w", encoding="utf-8") as f:
        for pair in pairs:
            if pair.a not in index or pair.b not in index:
                log(f"  skipping {pair.pair_id}: person not in population")
                continue
            for k in rc.ks:
                ctx = build_context(index[pair.a], index[pair.b], index, k)
                system, user = build_prompt(ctx)
                try:
                    reply = backend.complete(system, user)
                except Exception as exc:  # network / server errors: recorded, not fatal
                    reply = ""
                    log(f"  backend error on {pair.pair_id} k={k}: {exc}")
                v = parse_response(reply)
                faith = check_faithfulness(v.evidence, ctx)
                record = {"pair_id": pair.pair_id, "k": k, "gold": pair.label,
                          "verdict": v.verdict, "n_facts": len(ctx.facts),
                          "n_cited": faith.n_cited, "n_faithful": faith.n_faithful,
                          "unsupported": faith.unsupported, "evidence": v.evidence,
                          "rationale": v.rationale, "parse_error": v.error,
                          "prompt_sha1": hashlib.sha1(user.encode()).hexdigest(), "reply": reply}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                rows.append(record)
    summary = verification_metrics(pd.DataFrame(rows))
    summary.to_csv(out / "summary.csv", index=False)
    (out / "report.md").write_text(f"# RQ2 verification — {cfg.name} ({backend.name})\n\n"
                                   + markdown_table(summary) + "\n", encoding="utf-8")
    write_manifest(cfg, out, stage="rq2", backend=backend.name, n_pairs=len(pairs))
    log(f"RQ2 report written to {out / 'report.md'}")
    return summary
