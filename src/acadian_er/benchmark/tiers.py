"""Perturbation tiers, applied to a cloned family (in place).

Each tier function receives the cloned family {clone key: Personne}, the
cloned anchor key, a seeded RNG and the benchmark config, and returns a short
description of what it changed (stored with the query). Relatives' copies of
the anchor's name / birth year (`Proche`, `Mariage`) are kept consistent.

  t0_clean          unperturbed clone (control: upper bound for every method)
  t1_name           dropped first given name, else dit name used as surname,
                    else given-name variant (Marie -> Mary)
  t2_dates          anchor's dates removed or shifted by 1..date_shift_max years
  t3_parent_names   anchor's parents' names blanked
  t4_neighbourhood  most relatives dropped (keep_fraction kept)
  t5_one_line       only the paternal OR only the maternal line kept
"""

from __future__ import annotations

import random
from collections.abc import Callable

from genealogie_acadienne import Personne, alias_dit, normaliser
from genealogie_acadienne.commun.dates import decaler_date
from genealogie_acadienne.commun.variantes import GROUPES_PRENOMS
from genealogie_acadienne.commun.voisinage import Cle, cle, indexer, proches_par_role

from ..config import BenchmarkConfig

Family = dict[Cle, Personne]
_VARIANTS = {g[0]: g[1:] for g in GROUPES_PRENOMS}
DATED = ("BIRT", "BAPM", "DEAT", "BURI")


def _rename(family: Family, key: Cle, full: str, given: str, surname: str) -> None:
    p = family[key]
    p.nom_complet, p.nom_norm, p.prenoms, p.nom_famille = full, normaliser(full), given, surname
    for q in family.values():
        for x in q.parents + q.enfants + q.conjoints:
            if x.get("person_id") == key[1]:
                x["nom"], x["nom_norm"] = full, normaliser(full)
        for m in q.mariages:
            if m.get("conjoint_id") == key[1]:
                m["conjoint"], m["conjoint_norm"] = (full or None), (normaliser(full) or None)


def _remove(family: Family, keys: set[Cle]) -> None:
    gone = {k[1] for k in keys}
    for k in keys:
        family.pop(k, None)
    for q in family.values():
        for role in ("parents", "enfants", "conjoints"):
            setattr(q, role, [x for x in getattr(q, role) if x.get("person_id") not in gone])
        q.mariages = [m for m in q.mariages if m.get("conjoint_id") not in gone]


def t0_clean(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    return "none"


def t1_name(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    p = family[anchor]
    surname = p.nom_famille or (p.nom_complet.split()[-1] if p.nom_complet else "")
    base = p.nom_complet.split(" dit ")[0].split(" dite ")[0]
    given = p.prenoms.split() if p.prenoms else base.split()[:-1]
    if len(given) > 1:
        g = " ".join(given[1:])
        _rename(family, anchor, f"{g} {surname}", g, surname)
        return f"dropped first given name {given[0]!r}"
    dits = alias_dit(p.nom_complet)
    if dits:
        dit = dits[0].title()
        g = " ".join(given)
        _rename(family, anchor, f"{g} {dit}", g, dit)
        return f"dit name {dit!r} used as surname"
    for i, name in enumerate(given):
        options = _VARIANTS.get(normaliser(name))
        if options:
            new = list(given)
            new[i] = rng.choice(options).capitalize()
            g = " ".join(new)
            _rename(family, anchor, f"{g} {surname}", g, surname)
            return f"given-name variant {name!r} -> {new[i]!r}"
    return "no name perturbation possible"


def t2_dates(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    p = family[anchor]
    changes = []
    for fact in DATED:
        if not p.faits.get(fact):
            continue
        if rng.random() < cfg.date_drop_prob:
            p.faits.pop(fact)
            p.dates.pop(fact, None)
            changes.append(f"{fact} removed")
        else:
            shift = rng.choice([-1, 1]) * rng.randint(1, cfg.date_shift_max)
            p.faits[fact] += shift
            if fact in p.dates:
                p.dates[fact] = decaler_date(p.dates[fact], shift)
            changes.append(f"{fact} {shift:+d}y")
    for m in p.mariages:
        if m.get("annee"):
            m["annee"] = None
            m["date"] = None
            changes.append("MARR removed")
    birth = p.faits.get("BIRT")
    for q in family.values():          # relatives' view of the anchor's birth year
        for x in q.parents + q.enfants + q.conjoints:
            if x.get("person_id") == anchor[1]:
                x["naissance"] = birth
    return ", ".join(changes) or "no dates to perturb"


def t3_parent_names(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    roles = proches_par_role(family[anchor], indexer(family.values()))
    parents = roles["pere"] + roles["mere"] + roles["parents_inconnus"]
    for q in parents:
        _rename(family, cle(q), "", "", "")
    for x in family[anchor].parents:    # also parents outside the clone (none at depth >= 1)
        x["nom"], x["nom_norm"] = "", ""
    return f"{len(parents)} parent name(s) removed"


def t4_neighbourhood(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    others = sorted(k for k in family if k != anchor)
    n_keep = int(len(others) * cfg.keep_fraction)
    keep = set(rng.sample(others, n_keep))
    _remove(family, set(others) - keep)
    return f"kept {n_keep}/{len(others)} relatives"


def t5_one_line(family: Family, anchor: Cle, rng: random.Random, cfg: BenchmarkConfig) -> str:
    roles = proches_par_role(family[anchor], indexer(family.values()))
    lines = {"paternal": roles["pere"], "maternal": roles["mere"]}
    available = [name for name, ps in lines.items() if ps]
    if len(available) < 2:
        return "only one parent known: no line removed"
    kept = rng.choice(available)
    dropped = lines["maternal" if kept == "paternal" else "paternal"]
    # drop the other parent and everyone reachable only through them
    drop = {cle(q) for q in dropped}
    index = indexer(family.values())
    frontier = list(drop)
    while frontier:
        k = frontier.pop()
        for rel_key in [(k[0], x["person_id"]) for x in index[k].parents]:
            if rel_key in index and rel_key != anchor and rel_key not in drop:
                drop.add(rel_key)
                frontier.append(rel_key)
    _remove(family, drop)
    return f"kept {kept} line, removed {len(drop)} person(s)"


TIERS: dict[str, Callable[[Family, Cle, random.Random, BenchmarkConfig], str]] = {
    "t0_clean": t0_clean,
    "t1_name": t1_name,
    "t2_dates": t2_dates,
    "t3_parent_names": t3_parent_names,
    "t4_neighbourhood": t4_neighbourhood,
    "t5_one_line": t5_one_line,
}
