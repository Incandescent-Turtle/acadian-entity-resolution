"""Prompt for pairwise verification. Same instructions for k=0 and k=2; only the
facts differ."""

from __future__ import annotations

from .context import PairContext

SYSTEM = """You are an expert in Acadian genealogy helping to find duplicate people \
across family trees. Two records, A and B, come from different trees. Decide \
whether they describe the SAME real person.

Spelling varies a lot: Marie/Mary, Comeau/Comeaux, a first given name may be \
dropped ("Marie Louise" vs "Louise"), and "dit" names are aliases or alternative \
surnames. Dates may be approximate (ABT = about). Missing information is not \
evidence against a match.

Answer with ONE JSON object and nothing else:
{"verdict": "match" | "not_match" | "insufficient",
 "evidence": [{"id": "<fact id>", "value": "<value exactly as given>"}, ...],
 "rationale": "<one or two sentences>"}

Rules:
- Use "insufficient" when the facts cannot settle the question.
- Cite only fact ids that appear below, in square brackets, with their values copied exactly.
- Cite the facts that decided your verdict (agreements or contradictions), at most 8."""


def build_prompt(ctx: PairContext) -> tuple[str, str]:
    scope = ("the two records only" if ctx.k == 0
             else f"the two records and their relatives up to {ctx.k} steps away")
    user = (f"Facts ({scope}). Each line is [fact id] value.\n\n"
            f"{ctx.render()}\n\nAre A and B the same person? Reply with the JSON object only.")
    return SYSTEM, user
