"""Baseline: the old repo's method, through genealogie_acadienne.

Exact-name pooling (`nom_norm` equality, as in `trouver_noms_partages`) then the
number of concordant criteria (`criteres_concordants(comparer(a, b))`: birth,
baptism, death, burial, marriage, parents, children).

Within the shared relaxed-name candidate list, candidates in the query's
exact-name pool rank first; inside and outside the pool, more concordant
criteria rank higher. score = POOL_BONUS * in_pool + n_criteria.
"""

from __future__ import annotations

import numpy as np

from genealogie_acadienne import Personne, comparer, criteres_concordants

from genealogie_acadienne.commun.voisinage import Cle

POOL_BONUS = 100.0


class ExactNameCriteriaRanker:
    name = "exact_name"

    def __init__(self, people: dict[Cle, Personne]):
        self.people = people

    def score(self, query: Cle, candidates: list[Cle]) -> np.ndarray:
        q = self.people[query]
        scores = []
        for c in candidates:
            p = self.people[c]
            pool = bool(q.nom_norm) and q.nom_norm == p.nom_norm
            scores.append(POOL_BONUS * pool + len(criteres_concordants(comparer(q, p))))
        return np.array(scores, dtype=float)
