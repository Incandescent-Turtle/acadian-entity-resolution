"""Record-level augmentations for contrastive training (two noisy views of a person).

Generic record noise, applied independently to every node in a view: drop the
first given name, swap a given name for a variant, drop dated facts, shift
years, drop places. Graph noise (dropping family links) is done in `ego_batch`.

These are deliberately generic and NOT the benchmark tiers (no dit-name
swap, no blanking of parents' names, no line removal); see
docs/decisions/0004-contrastive-training.md for the leakage discussion.
"""

from __future__ import annotations

import copy
import random

from genealogie_acadienne import Personne, normaliser

from ..config import AugmentConfig
from ..lib_staging.noms_variantes import GROUPES_PRENOMS

_VARIANTS = {g[0]: g[1:] for g in GROUPES_PRENOMS}
_FACTS = ("BIRT", "BAPM", "DEAT", "BURI")


def augment(p: Personne, rng: random.Random, cfg: AugmentConfig) -> Personne:
    q = copy.copy(p)
    q.faits, q.dates, q.lieux = dict(p.faits), dict(p.dates), dict(p.lieux)
    q.mariages = [dict(m) for m in p.mariages]

    given = q.prenoms.split() if q.prenoms else []
    if not given:
        words = q.nom_complet.split()
        given = words[:-1] if len(words) > 1 else []
    surname = q.nom_famille or (q.nom_complet.split()[-1] if q.nom_complet.split() else "")
    changed = False
    if len(given) > 1 and rng.random() < cfg.drop_given_prob:
        given, changed = given[1:], True
    if given and rng.random() < cfg.name_variant_prob:
        i = rng.randrange(len(given))
        options = _VARIANTS.get(normaliser(given[i]))
        if options:
            given[i], changed = rng.choice(options).capitalize(), True
    if changed:
        q.prenoms = " ".join(given)
        q.nom_complet = f"{q.prenoms} {surname}".strip()
        q.nom_norm = normaliser(q.nom_complet)

    for fact in _FACTS:
        if fact in q.faits and rng.random() < cfg.drop_fact_prob:
            q.faits.pop(fact, None)
            q.dates.pop(fact, None)
        elif q.faits.get(fact) and rng.random() < cfg.shift_year_prob:
            q.faits[fact] += rng.randint(-cfg.shift_year_max, cfg.shift_year_max)
        if fact in q.lieux and rng.random() < cfg.drop_place_prob:
            q.lieux.pop(fact)
    for m in q.mariages:
        if m.get("annee") and rng.random() < cfg.drop_fact_prob:
            m["annee"] = None
    return q
