# 0006 — One relaxed-name candidate list; seeded tie-breaking

**Context.** Comparing rankers is only fair if they rank the same candidates. The old
method uses an *exact*-name pool, which would miss most of the tier-1 clones by
construction. Scores often tie, especially integer criteria counts.

**Decision.**
- **Candidates:** `lib_staging.candidats` gives every query one candidate list. A
  candidate must share a surname key (spelling variants and dit aliases) and at least
  one canonical given name. Clone trees and the opposite known sex are excluded.
- **Exact-name baseline:** inside that list, the old exact-name pool ranks first
  (+100), then the number of concordant criteria.
- **Ties:** broken by a CRC32 hash of (seed, query, candidate), never by list order.
- **Missing targets:** a target absent from the list has rank None. It counts as a miss
  and contributes 0 to MRR. Candidate recall is reported separately.

**Consequences.**
- All differences between methods come from scoring, not blocking.
- Blocking failures cap every method equally, and are visible as `candidate_recall`.
- Rankings are reproducible for a seed.
