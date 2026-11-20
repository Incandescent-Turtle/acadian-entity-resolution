# Data model

How `genealogie_acadienne`'s `Personne` maps onto our graph and features, and what
we **assume** versus what is **confirmed**. We have not seen the database yet.

Legend:
- **Confirmed**: read in the library code (`genealogie_acadienne` at `93a34cf`) or its
  documented statistics.
- **Assumed**: a guess about the real data, to check once we have access.
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

Statistics in the library's notes: 149,553 individuals and 149,594 name records; about
12,000 names shared by more than one person (316 Marie LeBlanc in 42 trees); CHR
appears about 4 times. These are **confirmed** (recorded by the user).

## `Personne` (library model) → our use

| Field | Content | Our use | Status |
| --- | --- | --- | --- |
| `tree_id`, `person_id` | `gedcom_id`, xref | node key `(tree_id, person_id)` | confirmed |
| `nom_complet`, `nom_norm` | main name, normalised | name features, candidates, exact-name pool | confirmed |
| `prenoms`, `nom_famille` | `n_givn`, `n_surn` (`@P.N.`/`@N.M.` → empty) | given-name and surname keys | confirmed fields; **assumed** that `n_givn`/`n_surn` are filled consistently |
| `noms_alternatifs` | other `wt_name` rows (`_AKA`, `_MARNM`, extra `NAME`) | extra candidate keys, record text | confirmed fields; **assumed** which `n_type`s occur |
| `sexe` | `M`/`F`/`U` | feature; candidates with opposite known sex are excluded | confirmed |
| `faits` | year per BIRT, BAPM, CHR, DEAT, BURI | year features, `comparer` | confirmed |
| `dates`, `lieux` | GEDCOM date text and place per fact, from `i_gedcom` | date shifts (tier 2), place features, RQ2 facts | confirmed parser; **assumed** PLAC is filled often enough to matter |
| `mariages` | year, spouse name, `conjoint_id`, date text, place | marriage-year feature, spouse links, RQ2 facts | confirmed |
| `parents`, `enfants`, `conjoints` | `Proche`: name, birth year, `person_id` | **typed edges** (`child_of`, `parent_of`, `spouse_of`) | confirmed |

## Graph

- **Nodes:** one per `Personne`.
- **Edges:** from `lib_staging.voisinage.tous_les_liens`, typed, always in both
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

## Assumptions about the real data (to check first)

1. **Dit names.**
   - *Assumed* they appear inside `n_full` ("Jean Doucet dit Laverdure"), as handled by
     `alias_dit`, the `appariement-prenoms` work and the library's notes.
   - They may also, or instead, be stored as separate name rows (`_AKA`, a second
     `NAME`) or as a GEDCOM `NICK`. Neither is read as a dit name today, though `_AKA`
     rows end up in `noms_alternatifs`.
2. **Name types.** *Assumed* `n_type` values include `NAME`, `_MARNM` and `_AKA`.
   Unverified.
3. **Given names.** *Assumed* `n_givn` holds all given names in order, so "dropped
   first given name" means removing the first token.
4. **Dates.**
   - *Assumed* GEDCOM dates are standard (English months, ABT/BEF/AFT/BET).
   - French month abbreviations are also accepted in case of manual entry.
   - Dual dating (1745/46) keeps the first year.
5. **Places.** *Assumed* free-text PLAC strings ("Grand-Pré, Acadie"). They are hashed
   by token; places are not standardised.
6. **Sex.** *Assumed* mostly M/F; `U` is treated as compatible with both.
7. **Families.**
   - *Assumed* at most two parents per child family (FAMC). Several FAMC records
     (e.g. adoptive) would add more `child_of` edges, which is not distinguished.
   - Same-sex or unknown-sex couples are handled without special cases.
8. **Overlap between trees.**
   - *Assumed* trees overlap heavily on early Acadian families, which is why duplicates
     exist.
   - The synthetic generator imposes this by building trees from shared founders.
9. **Excluded trees.** The library already skips `FAMILLES.ACADIENNES`, `BABIN_TEST` and
   `MY_PROJECT`. *Assumed* this is right for the research as well.

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
