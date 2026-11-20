"""Faithfulness: does every piece of cited evidence exist in the context given?

A citation is faithful when its id is one of the context's fact ids AND its
value matches that fact (after normalisation; a cited value contained in the
fact, or vice versa, counts — models often shorten "ABT 12 MAR 1745" to
"1745"). An empty cited value counts as id-only: faithful if the id exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from genealogie_acadienne import normaliser

from .context import PairContext


@dataclass
class Faithfulness:
    n_cited: int
    n_id_found: int
    n_faithful: int
    unsupported: list[dict]

    @property
    def rate(self) -> float | None:
        return self.n_faithful / self.n_cited if self.n_cited else None

    @property
    def all_faithful(self) -> bool:
        return self.n_faithful == self.n_cited


def check_faithfulness(evidence: list[dict], ctx: PairContext) -> Faithfulness:
    facts = ctx.by_id()
    found = faithful = 0
    unsupported = []
    for item in evidence:
        fid, cited = item.get("id", ""), normaliser(item.get("value", ""))
        if fid not in facts:
            unsupported.append({**item, "reason": "unknown id"})
            continue
        found += 1
        actual = normaliser(facts[fid])
        if not cited or cited in actual or (actual and actual in cited):
            faithful += 1
        else:
            unsupported.append({**item, "reason": f"value differs from {facts[fid]!r}"})
    return Faithfulness(len(evidence), found, faithful, unsupported)
