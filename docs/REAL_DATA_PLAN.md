# Moving the pipeline to the real data

The pipeline runs end to end, but it was designed and tested before the full database was
available. On 2026-11-26 `scripts/audit_real_data.py` checked our assumptions against the
export (results in `DATA_MODEL.md`, "Assumptions about the real data"). This document lists
what has to change because of that, in order. Items marked **decision** need the user's OK
before any code changes.

Rerun the audit with:
```bash
uv run python scripts/audit_real_data.py --config configs/rq1_webtrees.yaml   # ~1 min, 1.6 GB
```

## Summary of the findings that matter
- The plumbing is fine: loaders, snapshot, graph and candidates work at full scale (2-hop
  neighbourhoods have a median of 11 people, max 106; 16,661 people qualify as anchors).
- **No real ground truth comes for free.** Shared `_UID`s only mark copies of whole trees.
  RQ1 stays clone-based, and RQ2's hand labels remain the only real evaluation.
- **HANKINSON was imported from the HARRINGTON file**, so the same 203 records are in the
  snapshot twice.
- **Dit names are mostly nicknames** (the name the person went by), not alternative
  surnames. Our tier 1 and the library's candidate keys treat them as surnames.
- **The data is mostly 19th–20th century** (median year 1895), sparser than the synthetic
  data (birth year 45%, places 20–30%), and has no married-name or `_AKA` rows.
- **Overlap between trees is modest.** Only 4.9% of people with a birth year have someone
  with the same name and year in another tree, so real matches will be rare among RQ2
  candidates.

## Step 1 — decisions (user)
1. **HANKINSON / HARRINGTON.** Drop HANKINSON, the mislabelled copy (proposed: add it to the
   library's `ARBRES_IGNORES`, since it is a property of the database). If both stay, an anchor in
   either tree has a second perfect match besides its clone's original, which distorts RQ1
   ranks, and RQ2 candidates would be full of trivial pairs. **decision**
2. **Tier 1 with nickname dits.** Today `t1_name` uses the dit as the *surname* ("Timothée
   Tim"). What happens in the data is that another tree records the nickname as the
   *given name* ("Tim Comeau" for "Timothée COMEAU dit Tim"). Proposed: rename the
   perturbation to "dit nickname used as given name" and add a surname-dit variant only
   when the alias really is a surname. This changes the research design (RESEARCH_DESIGN.md
   tier table). **decision**
3. **Where RQ2 pairs come from.** With few real matches, the top-N candidates of a ranker
   will be mostly non-matches. Proposed: mix ranker top-N with old-method pairs that meet
   several criteria (`person_comparisons` with `n_criteria >= 4`: 541 pairs, fewer once the
   HANKINSON/HARRINGTON copies are removed), and record
   each pair's origin (`source` already exists). **decision**
4. **Sources and notes** (343k citations, 117k notes). Proposed: leave them out of RQ1 and
   RQ2 for now and mention them as future work. Shared source titles could later be
   a signal, or RQ2 context. **decision**

## Step 2 — library fixes (`genealogie-acadienne`, then push and bump the pin)
1. `donnees.noms.ARBRES_IGNORES`: add the duplicate tree (if decided in 1.1).
2. `commun.variantes.cles_noms_famille`: stop using a dit alias as a surname key when it is
   one of the person's own given names (63% of dits). Today "dite Léa" adds a surname key
   `lea`, which only adds noise to the candidates. Keep it when it is not a given name.
3. `commun.variantes.GROUPES_PRENOMS`: add the nickname forms the audit shows (Harry →
   Henri, Hattie → Henriette, Bob → Robert, Ralph → Raphaël, Tim → Timothée, Alphée →
   Alpheus…). Take the list from the audit's "other nickname" rows; the library's tests
   must not use real data, so write them with made-up names.
4. `commun.noms`: handle alternatives in parentheses ("Michel (Pierre) DUGAS", "Johnson
   (Jeanson)", "(dit Jasmin)") and "dit X dit Y" / "dite soit X ou Y".
5. `commun.dates.analyser_date`: accept "A OR B" (0.3% of dates), for example as an
   interval from A to B.
6. After 2–4, rerun the audit and compare candidate-list sizes (now median 17, p90 275,
   max 2,033) and the share of people with no candidate (19%).

## Step 3 — project changes
1. `benchmark/tiers.py`: tier 1 as decided in 1.2. Also report how often each tier-1
   variant fires: only about 40% of people have two given names, so "dropped first given
   name" cannot apply to most anchors.
2. Features (`graph/features.py`): set `year_center` near the real median (about 1850–1900
   instead of 1750) in the real-data configs. Leave out generic place tokens ("nouvelle",
   "ecosse", "canada", "comte", "?") or keep only the first non-empty level, because
   they dominate the 32-dim hash today. Standardising places through `wt_places` is
   optional, later.
3. RQ2 (`experiments/rq2.py`): candidate mix as decided in 1.3.
4. Docs: RESEARCH_DESIGN.md (threats: no real RQ1 ground truth, nickname dits, modest
   overlap, anchor bias: anchors need a score ≥ 4 while the median person has 3).

## Step 4 — make the synthetic data look like the real data (library `commun.synthetique`)
Tests and dev runs keep using synthetic data, so it should match what we measured:
- period: 19th–20th century as well, not only founders in 1640–1680;
- fill rates: birth year about 45%, baptism 25%, death 14%, burial 9%, marriage 42%;
  places 20–30%;
- given names: 60% one, 37% two, 3% more;
- dits on about 10% of names, mostly nicknames from the person's own given names, some
  "X ou Y";
- no married-name rows.

Update the "What the synthetic generator imposes" section of DATA_MODEL.md to match.

## Step 5 — small real-data run
Run `rq1` on the real snapshot with a few anchors (e.g. `n_anchors: 20`, 1–2 epochs) to
check time and memory on the 8 GB laptop before any full run. Watch the queries with the
largest candidate lists (up to about 2,000) and the sentence-transformer encoding of the
whole snapshot.

## Step 6 — full runs
`rq1` with `clone_depth` 1 and 2 (configs exist), then `rq2-candidates`, hand labelling,
and `rq2`.
