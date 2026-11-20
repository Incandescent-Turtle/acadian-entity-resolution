# 0009 — Clone depth: run immediate family and 2 hops side by side

**Status: accepted (2026-11-20).**

**Context.** The specification says to clone the anchor "plus their immediate family".
At k=2, the *original's* neighbourhood includes grandparents, siblings and in-laws, but
the *clone's* only reaches what was cloned. Every 2-hop path in the clone has to stay
inside {anchor, parents, spouses, children}.

**Decision.** Run RQ1 twice and report both:
- `clone_depth: 1`, the immediate family, as specified. This is the main result
  (`configs/rq1_webtrees.yaml`).
- `clone_depth: 2`, the full 2-hop neighbourhood copied, as a sensitivity analysis
  (`configs/rq1_webtrees_depth2.yaml`). Synthetic counterpart:
  `configs/dev_synthetic_depth2.yaml`.

Both use the same seed, so they select the same anchors.

**Consequences.**
- The depth-1 run probably understates what 2 hops can add. The depth-2 run shows how
  much, but its clones carry more copied structure, which makes them easier for every
  graph method.
- Each tier must stay meaningful at depth 2:
  - t4 drops most of the copied relatives;
  - t5 drops the other parent and that parent's ancestors (siblings, shared with the kept parent, stay);
  - t3 blanks the parents' names only.
