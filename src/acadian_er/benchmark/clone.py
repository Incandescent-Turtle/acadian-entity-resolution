"""Choose well-documented anchors and clone them, with their family, into a dummy tree."""

from __future__ import annotations

import copy
import random

from genealogie_acadienne import Personne

from ..lib_staging.voisinage import Cle, cle, construire_adjacence, voisinage

DATED = ("BIRT", "BAPM", "DEAT", "BURI")


def documentation_score(p: Personne) -> int:
    """Number of filled attribute fields: dated facts, marriage year, given name, surname."""
    n = sum(1 for f in DATED if p.faits.get(f))
    n += any(m.get("annee") for m in p.mariages)
    n += bool(p.prenoms or len(p.nom_complet.split()) > 1)
    n += bool(p.nom_famille)
    return n


def family_size(p: Personne, index: dict[Cle, Personne]) -> int:
    """Relatives (parents, spouses, children) present in the tree."""
    ids = {x.get("person_id") for x in p.parents + p.conjoints + p.enfants}
    return sum(1 for x in ids if x and (p.tree_id, x) in index)


def select_anchors(index: dict[Cle, Personne], n: int, rng: random.Random,
                   min_fields: int, min_family: int, exclude: set[Cle] = frozenset()) -> list[Cle]:
    """Sample up to `n` well-documented people (enough fields AND relatives).
    Ties in ordering are resolved by the seeded sample, never by dict order."""
    eligible = sorted(
        k for k, p in index.items()
        if k not in exclude and documentation_score(p) >= min_fields
        and family_size(p, index) >= min_family
    )
    return sorted(rng.sample(eligible, min(n, len(eligible))))


def clone_family(anchor: Cle, index: dict[Cle, Personne], tree_id: int, prefix: str,
                 depth: int = 1, adjacency=None) -> tuple[dict[Cle, Personne], Cle]:
    """Copy `anchor` and everyone within `depth` hops into tree `tree_id`.

    Returns ({original key: cloned Personne}, cloned anchor key). Relatives
    outside the copied set are removed from the clones' lists, and every
    `person_id` / `conjoint_id` is remapped to the new xrefs (`prefix` + n).
    """
    members = sorted(voisinage(anchor, index, depth, adjacency or construire_adjacence(index)),
                     key=lambda k: (k != anchor, k))
    new_id = {k[1]: f"{prefix}{n}" for n, k in enumerate(members)}
    clones: dict[Cle, Personne] = {}
    for k in members:
        p = copy.deepcopy(index[k])
        p.tree_id, p.person_id = tree_id, new_id[k[1]]
        for role in ("parents", "enfants", "conjoints"):
            setattr(p, role, [dict(x, person_id=new_id[x["person_id"]])
                              for x in getattr(p, role) if x.get("person_id") in new_id])
        p.mariages = [dict(m, conjoint_id=new_id[m["conjoint_id"]]) for m in p.mariages
                      if m.get("conjoint_id") in new_id]
        clones[k] = p
    return clones, cle(clones[anchor])
