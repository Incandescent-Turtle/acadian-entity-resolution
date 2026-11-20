"""The ranker interface shared by baselines and the R-GCN."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ..lib_staging.voisinage import Cle


class Ranker(Protocol):
    name: str

    def score(self, query: Cle, candidates: list[Cle]) -> np.ndarray:
        """One score per candidate (higher = more likely the same person)."""
        ...


def cosine_scores(embeddings: dict[Cle, np.ndarray], query: Cle, candidates: list[Cle]) -> np.ndarray:
    """Dot products of L2-normalised vectors (= cosine similarity)."""
    if not candidates:
        return np.zeros(0)
    q = embeddings[query]
    return np.stack([embeddings[c] for c in candidates]) @ q
