"""The evidence an LLM sees for a pair, as facts with stable IDs.

k = 0: each record's OWN attributes only (names, sex, dates, places, marriage
       dates/places) — no relative's name, same as RQ1's attribute-only view.
k = 2: plus every relative within 2 hops, addressed by role path:
       A.father, A.mother, A.spouse1, A.child2, A.father.mother (grandmother),
       A.spouse1.father (father-in-law), A.child1.spouse1, A.father.child3 (sibling)...

Fact IDs look like `A.birth.date`, `B.father.name`, `A.spouse1.death.place`.
The faithfulness check later verifies that every cited ID exists here and
that the cited value matches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from genealogie_acadienne import Personne

from genealogie_acadienne.commun.voisinage import Cle, cle, proches_par_role

FACTS = {"BIRT": "birth", "BAPM": "baptism", "DEAT": "death", "BURI": "burial"}


@dataclass(frozen=True)
class Fact:
    id: str
    value: str


@dataclass
class PairContext:
    a: Cle
    b: Cle
    k: int
    facts: list[Fact] = field(default_factory=list)

    def by_id(self) -> dict[str, str]:
        return {f.id: f.value for f in self.facts}

    def render(self) -> str:
        return "\n".join(f"[{f.id}] {f.value}" for f in self.facts)


def record_facts(prefix: str, p: Personne) -> list[Fact]:
    facts = [Fact(f"{prefix}.name", p.nom_complet or "(no name)"),
             Fact(f"{prefix}.sex", {"M": "male", "F": "female"}.get(p.sexe, "unknown"))]
    facts += [Fact(f"{prefix}.alt_name{i + 1}", n) for i, n in enumerate(p.noms_alternatifs)]
    for code, label in FACTS.items():
        date = p.dates.get(code) or (str(p.faits[code]) if p.faits.get(code) else None)
        if date:
            facts.append(Fact(f"{prefix}.{label}.date", date))
        if p.lieux.get(code):
            facts.append(Fact(f"{prefix}.{label}.place", p.lieux[code]))
    for i, m in enumerate(p.mariages):
        date = m.get("date") or (str(m["annee"]) if m.get("annee") else None)
        if date:
            facts.append(Fact(f"{prefix}.marriage{i + 1}.date", date))
        if m.get("lieu"):
            facts.append(Fact(f"{prefix}.marriage{i + 1}.place", m["lieu"]))
    return facts


def _relatives(p: Personne, index: dict[Cle, Personne]) -> list[tuple[str, Personne]]:
    roles = proches_par_role(p, index)
    out = [("father", q) for q in roles["pere"][:1]] + [("mother", q) for q in roles["mere"][:1]]
    out += [(f"parent{i + 1}", q) for i, q in enumerate(roles["parents_inconnus"])]
    out += [(f"spouse{i + 1}", q) for i, q in enumerate(roles["conjoints"])]
    out += [(f"child{i + 1}", q) for i, q in enumerate(sorted(roles["enfants"], key=_birth_order))]
    return out


def _birth_order(p: Personne):
    return (p.faits.get("BIRT") or 9999, p.person_id)


def neighbourhood_facts(prefix: str, p: Personne, index: dict[Cle, Personne], k: int) -> list[Fact]:
    facts: list[Fact] = []
    seen = {cle(p)}
    frontier = [(prefix, p)]
    for _ in range(k):
        nxt = []
        for path, q in frontier:
            for role, r in _relatives(q, index):
                if cle(r) in seen:
                    continue
                seen.add(cle(r))
                facts += record_facts(f"{path}.{role}", r)
                nxt.append((f"{path}.{role}", r))
        frontier = nxt
    return facts


def build_context(a: Personne, b: Personne, index: dict[Cle, Personne], k: int) -> PairContext:
    ctx = PairContext(cle(a), cle(b), k)
    for prefix, p in (("A", a), ("B", b)):
        ctx.facts += record_facts(prefix, p)
        if k > 0:
            ctx.facts += neighbourhood_facts(prefix, p, index, k)
    return ctx
