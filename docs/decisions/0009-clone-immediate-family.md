# 0009 — Clone only the immediate family (proposed)

**Status: proposed. Needs the user's confirmation.**

**Context.** The specification says to clone the anchor "plus their immediate family".
At k=2, the *original's* neighbourhood includes grandparents, siblings and in-laws, but
the *clone's* only reaches what was cloned. Every 2-hop path in the clone has to stay
inside {anchor, parents, spouses, children}: parent → anchor's sibling does not exist,
and so on.

**Decision (for now).** `benchmark.clone_depth: 1`: the immediate family, as specified.
The depth is configurable (`clone_depth: 2` copies the full 2-hop neighbourhood).

**Consequences.**
- k=2 sees nearly the same information as k=1 on the clone side, so RQ1 probably
  **understates** what 2 hops can add. Real duplicates in another tree usually come
  with their own wider family.
- Options:
  - (a) keep depth 1 and report this;
  - (b) clone at depth 2 for every tier;
  - (c) run both as a sensitivity analysis. Recommended.
