"""Rank of the true duplicate, Recall@K and MRR.

Ties are broken by a seeded hash of (seed, query, candidate), never by list
order, so no method profits from the candidate order. A target missing from
the candidate list has rank None: it counts as a miss for Recall@K and adds 0
to MRR (the candidate generator's recall is reported separately as
`candidate_recall`).
"""

from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from genealogie_acadienne.commun.voisinage import Cle


def _tiebreak(seed: int, query: Cle, cand: Cle) -> float:
    return zlib.crc32(f"{seed}|{query}|{cand}".encode()) / 2**32


def rank_of_target(scores: np.ndarray, candidates: list[Cle], target: Cle, query: Cle,
                   seed: int = 0) -> int | None:
    """1-based rank of `target` among `candidates` (None if absent)."""
    if target not in candidates:
        return None
    t = candidates.index(target)
    st, tb = scores[t], _tiebreak(seed, query, target)
    better = 0
    for i, c in enumerate(candidates):
        if i == t:
            continue
        if scores[i] > st or (scores[i] == st and _tiebreak(seed, query, c) > tb):
            better += 1
    return better + 1


def summarise(rows: pd.DataFrame, ks: list[int]) -> pd.DataFrame:
    """rows: one per (method, tier, query) with column `rank` (None = missing).
    Returns one row per (method, tier) plus an 'all' tier."""
    out = []
    groups = list(rows.groupby(["method", "tier"], sort=False))
    groups += [((m, "all"), g) for m, g in rows.groupby("method", sort=False)]
    for (method, tier), g in groups:
        ranks = g["rank"]
        found = ranks.notna()
        rec = {"method": method, "tier": tier, "n_queries": len(g),
               "candidate_recall": float(found.mean()),
               "mean_candidates": float(g["n_candidates"].mean())}
        for k in ks:
            rec[f"recall@{k}"] = float(((ranks <= k) & found).mean())
        rec["mrr"] = float(np.where(found, 1.0 / ranks.where(found, 1.0), 0.0).mean())
        out.append(rec)
    return pd.DataFrame(out)
