# Data model

How `genealogie_acadienne`'s `Personne` maps onto our graph and features, and what
we **assume** versus what is **confirmed**. The assumptions below were checked against the
offline export on 2026-11-26 with `scripts/audit_real_data.py` (report in
`results/audit/audit.md`, not committed); what follows from them is in `REAL_DATA_PLAN.md`.
Practical notes on the dataset for future researchers are in `DATASET_NOTES.md`.

Legend:
- **Confirmed**: read in the library code (`genealogie_acadienne` at `93a34cf`) or its
  documented statistics.
- **Assumed**: a guess about the real data, to check once we have access.
- **Refuted**: an assumption the audit showed to be wrong.
- **Synthetic**: a property our generator imposes, which the real data may not share.

## Source: WebTrees tables read by the library

| Table | Used for | Status |
| --- | --- | --- |
| `wt_individuals` (`i_id`, `i_file`, `i_sex`, `i_gedcom`) | person, sex, raw GEDCOM (full dates, places) | confirmed (queries in `donnees/personnes.py`) |
| `wt_name` (`n_id`, `n_file`, `n_num`, `n_type`, `n_full`, `n_givn`, `n_surn`) | names; first `NAME` by `n_num` is the main name | confirmed |
| `wt_families` (`f_id`, `f_husb`, `f_wife`, `f_gedcom`) | couples, marriage place/date text | confirmed |
| `wt_link` (`l_type` FAMC / FAMS / CHIL) | parent/child/spouse links | confirmed |
| `wt_dates` (`d_fact`, `d_year`) | years of BIRT, BAPM, CHR, DEAT, BURI, MARR | confirmed |
| `wt_gedcom` | tree names; `FAMILLES.ACADIENNES`, `BABIN_TEST`, `MY_PROJECT` are skipped | confirmed |

We read these tables from the offline Parquet export (`../data/parquet/`, from the
`webtree-testing.sql` dump) through an in-memory SQLite copy, with the same SQL as on
MariaDB. **Confirmed (2026-11-26)** that the two agree: on the export, the library's
`genealogie-apparier` reproduces the 29,980 pairs of the `person_comparisons` table made
earlier on MariaDB (same pairs, same values), and `genealogie-statistiques` reproduces
`rapports/statistiques.md`. SQLite compares text with case sensitivity where MariaDB
usually ignores case; WebTrees codes (`NAME`, `FAMC`...) and xrefs are stored consistently. First snapshot (2026-11-26): 140,248 people in 66 trees after
skipping 9,305 in the ignored trees.

Statistics in the library's notes: 149,553 individuals and 149,594 name records; about
12,000 names shared by more than one person (316 Marie LeBlanc in 42 trees); CHR
appears about 4 times. These are **confirmed** (recorded by the user).

## `Personne` (library model) → our use

| Field | Content | Our use | Status |
| --- | --- | --- | --- |
| `tree_id`, `person_id` | `gedcom_id`, xref | node key `(tree_id, person_id)` | confirmed |
| `nom_complet`, `nom_norm` | main name, normalised | name features, candidates, exact-name pool | confirmed |
| `prenoms`, `nom_famille` | `n_givn`, `n_surn` (`@P.N.`/`@N.M.` → empty) | given-name and surname keys | confirmed fields; **assumed** that `n_givn`/`n_surn` are filled consistently |
| `noms_alternatifs` | other `wt_name` rows (`_AKA`, `_MARNM`, extra `NAME`) | extra candidate keys, record text | confirmed fields; in the real data only extra `NAME` rows, for 28 people (audit) |
| `sexe` | `M`/`F`/`U` | feature; candidates with opposite known sex are excluded | confirmed |
| `faits` | year per BIRT, BAPM, CHR, DEAT, BURI | year features, `comparer` | confirmed |
| `dates`, `lieux` | GEDCOM date text and place per fact, from `i_gedcom` | date shifts (tier 2), place features, RQ2 facts | confirmed parser (99.7% of dates parse); places are sparse: birth 28%, baptism 21%, marriage 32% (audit) |
| `mariages` | year, spouse name, `conjoint_id`, date text, place | marriage-year feature, spouse links, RQ2 facts | confirmed |
| `parents`, `enfants`, `conjoints` | `Proche`: name, birth year, `person_id` | **typed edges** (`child_of`, `parent_of`, `spouse_of`) | confirmed |

## Graph

- **Nodes:** one per `Personne`.
- **Edges:** from `genealogie_acadienne.commun.voisinage.tous_les_liens`, typed, always in both
  directions:
  - `parent_of` (parent → child) and its inverse `child_of`;
  - `spouse_of` (symmetric), from `conjoints` and from `mariages[].conjoint_id`.
- **Within one tree only.** An xref means nothing outside its tree. Cross-tree identity
  is exactly what we are trying to find, so there are no cross-tree edges.
- **Missing relatives:** a relative listed in `Proche` but not loaded gives no edge (it
  is still visible in `comparer`).

## Node features (`graph.features`, attribute-only)

| Block | Size (default) | Content |
| --- | --- | --- |
| given | 128 | hashed canonical given names (Marie = Mary; dit aliases included) + their character trigrams, L2-normalised |
| surname | 64 | hashed character trigrams of the surname key(s) (Comeau = Comeaux; dit alias as a second surname) |
| sex | 3 | one-hot M / F / unknown |
| years | 10 | for BIRT, BAPM, DEAT, BURI, first MARR: present flag + (year − 1750) / 100 |
| place | 32 | hashed tokens of the birth or baptism place |

Relatives' names are **not** features. Family information reaches the model only through
edges, so k=0 is attribute-only.

## Assumptions about the real data (checked 2026-11-26)

Numbers are from the audit, on the raw export (149,553 people, 69 trees) or the snapshot
(140,248 people, 66 trees, ignored trees removed).

1. **Dit names. Partly refuted.**
   - **Confirmed:** dit names sit inside `n_full`, after the surname (99.8%), marked `dit`
     or `dite`. 10.3% of name rows have one.
   - **Refuted:** that a dit is usually an alternative *surname*. 63% of aliases are a
     form of the person's own given names, i.e. the name they went by ("Marie Léa Comeau
     dite Léa"). Another 26% are other nicknames ("dit Harry", "dit Joe", "dit l'aîné").
     At most 7% match a surname in the database, and even those are often nicknames
     ("dite Hattie").
   - 5% have several aliases ("dit Alphée ou Alpheus", "dite soit Rosalie ou Rose Anne",
     "dit X dit Y"). Parentheses also carry alternatives: "Michel (Pierre) DUGAS",
     "Johnson (Jeanson)", "(dit Jasmin)".
2. **Name types. Refuted.** `n_type` is always `NAME`. There are no `_MARNM` or `_AKA`
   rows; only 41 people have a second name row (28 after the ignored trees).
3. **Given names. Confirmed.** `n_givn` is filled (99.8%) and is always contained in
   `n_full`. 60% of people have one given name, 37% two, 3% three or more, so a
   "dropped first given name" is only possible for about 40%.
   Surnames are in capitals in about a third of the rows (tree convention).
4. **Dates. Confirmed.**
   - 99.7% of 169,582 event dates parse with `analyser_date`; 93% are exact, 6% `ABT`, the
     rest `BEF`/`AFT`/`BET`. Months are English GEDCOM abbreviations; no French months and
     no dual dating seen. 8 Julian dates.
   - The unparsed 0.3% are mostly alternatives ("22 AUG 1892 OR 25 AUG 1892", "1706 OR
     1707") and day-month without a year.
   - **Not as assumed:** the period. Median year 1895, 90th percentile 1949; the data is
     mostly 19th–20th century, not the 17th–18th. A few typo years (150, 2977).
   - `DEAT` appears on 100% of records but has a date on only 14% (a bare `1 DEAT` means
     "deceased").
5. **Places. Confirmed free text, sparse.** 11,519 distinct `PLAC` strings, comma-separated,
   1–9 levels (median 3), with inconsistent forms for the same place ("Meteghan, comté de
   Digby, Nouvelle-Écosse" vs "?, , , , CANADA, Meteghan, Nouvelle-Écosse").
   `wt_places` holds a per-tree hierarchy and `wt_place_location` has coordinates for 74%
   of its rows; neither is used yet.
6. **Sex. Confirmed.** M 50.5%, F 49.1%, U 0.4%.
7. **Families. Confirmed.**
   - At most one FAMC per person (63.5% have one). `PEDI` is `birth` except 9 `adopted`.
   - 8 same-sex couples and 13 U/U couples, likely data errors; 2,400 families with one
     spouse missing. 27,542 families have no children.
   - 2-hop neighbourhoods are small: median 11 people, p99 61, max 106.
8. **Overlap between trees. Weaker than assumed.**
   - 19% of people have no candidate at all in another tree (no shared surname key and
     given name). 46% have a candidate with exactly the same name, but of the people with
     a birth year only 4.9% have one with the same name *and* year.
   - **`_UID` is not a ground truth.** 7,113 `_UID`s occur in several trees, but they come
     from copies of whole trees: `FAMILLES.ACADIENNES` is AMIRAULT + BABIN + ALLAIN
     (6,910 = 4,515 + 1,912 + 483), and `babin_test` is a copy of BABIN. Only 203 pairs
     survive in the snapshot, and they are another whole-tree copy (below).
   - **New:** HANKINSON (39) was imported from `HARRINGTON_cleaned.ged`, so it holds the
     same 203 records as HARRINGTON (40). Both are in the snapshot, so they form 203
     trivial duplicates (see `DATASET_NOTES.md`).
   - `REFN` is a per-tree counter, not an identity.
9. **Excluded trees. Confirmed right.** The three ignored trees are copies or tests
   (above). `babin_test` is spelled in lowercase in `wt_gedcom` but is still skipped
   (9,305 people removed = 6,910 + 1,912 + 483).

Not modelled yet: 343k source citations (`SOUR`, 7,537 sources; 541 source titles appear
in several trees) and 117k notes. `person_comparisons` (the old method's 29,980 pairs)
has 201 pairs sharing a `_UID`, i.e. the HANKINSON/HARRINGTON copy.

## What the synthetic generator imposes (synthetic, not facts about the real data)

- Founders born 1640–1680; generations 19–27 years apart; up to 10 children.
- About 55% of girls have "Marie" as their first given name.
- 40 Acadian surnames, 12 of them with dit names; surname spelling variants from a
  fixed table.
- Each tree has its own noise rates:
  - missing dates 10–50%;
  - missing places 20–70%;
  - wrong year 0–10%;
  - dropped first given name 0–30%;
  - surname variant 0–40%;
  - dit name shown 0–60%;
  - about 20% of trees anglicise given names.
- Trees are descendants of a founder (or a later person) over 3 generations, plus
  spouses and the spouses' parents.
- Only BIRT, BAPM, DEAT, BURI and MARR are generated; no CHR, no extra NAME rows apart
  from a married name for some women.
