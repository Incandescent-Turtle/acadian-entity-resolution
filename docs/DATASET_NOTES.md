# Notes on the dataset

Practical notes on the Acadian WebTrees database, for anyone who works with it after us:
traps, quirks, and what turned out *not* to be useful. They describe the dump
`webtree-testing.sql` (sha256 `e050c18a…`, exported to `../data/parquet/`). Numbers come
from `scripts/audit_real_data.py` unless stated; rerun it on a newer dump before relying on
them. How the data maps onto our model is in `DATA_MODEL.md`.

## What it is
- One WebTrees install, 69 trees (`wt_gedcom`) with 149,553 individuals. Most trees are named
  after a family (COMEAU, LEBLANC, DOUCET…) and are maintained separately, so the same
  person can appear in several of them. Sizes range from 41 to 10,627 people (median 1,100).
- Tables: `wt_individuals` (one GEDCOM record per person, in `i_gedcom`), `wt_name`,
  `wt_families`, `wt_link` (every xref reference: FAMC, FAMS, CHIL, HUSB, WIFE, SOUR, NOTE,
  REPO), `wt_dates`, `wt_places`, `wt_place_location`, `wt_sources`, `wt_other` (notes,
  repositories). `person_comparisons` is not a WebTrees table: it holds the 29,980 pairs
  made by the earlier exact-name method.
- xrefs (`@I123@`) are only unique **within** a tree; always key people by
  `(tree_id, person_id)`.

## Trees to exclude
| id | Tree | Why |
| --- | --- | --- |
| 71 | `FAMILLES.ACADIENNES` | Copy of AMIRAULT + BABIN + ALLAIN (6,910 = 4,515 + 1,912 + 483 people, same `_UID`s). Imported from `Amirault__.ged`. |
| 72 | `babin_test` | Test copy of BABIN (1,912 people). Lowercase in `wt_gedcom`. |
| 70 | `MY_PROJECT` | Test project (483 people, from a Gramps export). |
| 39 | `HANKINSON` | **Wrong file imported.** Its `gedcom_filename` is `HARRINGTON_cleaned.ged`: it holds the same 203 people as HARRINGTON (40), with the same xrefs and identical records, mostly Harringtons. The real Hankinson tree is not in the database. **Not excluded by the library yet.** |
| -1 | `DEFAULT_TREE` | WebTrees placeholder, no people. |

The library skips the first three (`genealogie_acadienne.donnees.noms.ARBRES_IGNORES`;
140,248 people remain). Until HANKINSON is added, every HARRINGTON person has a perfect
duplicate. These account for all 201 `person_comparisons` pairs that share a `_UID`. Worth
telling whoever maintains the site.

To spot this kind of problem: compare `gedcom_filename` with `gedcom_name`, and look for tree
pairs that share many `_UID`s (the audit lists them).

## Identifiers that look useful but aren't
- **`_UID`** (on 65% of records with a value): it does **not** link the same person across
  independently built trees. Of the 7,113 `_UID`s found in more than one tree, all come from
  the whole-tree copies above. In the clean trees, no two trees share a `_UID`. So it gives
  no ground truth for duplicates.
- **`REFN`**: a per-tree record counter (`1056`, `4416`…), not an identity.
- **`n_soundex_*`, `p_*_soundex`**: WebTrees' own phonetic codes. They are tuned for English and
  have not been evaluated here.

## Names
- `wt_name.n_type` is always `NAME`: there are no `_MARNM` (married name) or `_AKA` rows.
  Only 41 people have two name rows. Alternative names live **inside** `n_full`.
- `n_givn` / `n_surn` are reliable (filled for 99.8%, `n_givn` always inside `n_full`).
  About a third of the trees write surnames in CAPITALS.
- 60% of people have one given name, 37% two, 3% three or more.
- **Dit names** (10.3% of names) are written after the surname as `dit` / `dite`:
  "Timothée COMEAU dit Tim", "Marie Léa Comeau dite Léa". They are the name the person went
  by (an aka), usually a form of one of their own given names (63%) or a nickname (26%: Harry,
  Joe, Hattie, l'aîné). Few are surnames. Another tree may know the person **only** by that
  name ("Tim Comeau", or no proper given name at all), so a dit should be treated as a
  possible given name when matching.
  - 5% list several: "dit Alphée ou Alpheus", "dite soit Rosalie ou Rose Anne", "dit X dit Y".
  - Parentheses also carry alternatives: "Michel (Pierre) DUGAS", "Johnson (Jeanson)",
    "(dit Jasmin)", and question marks mark doubt ("McDcollt (?)").
- Expect English and French forms of the same name across trees (Marie/Mary, Henri/Harry),
  and surname spelling variants (Comeau/Comeaux, Doucet/Doucette).

## Dates and events
- Dates are standard GEDCOM (English month abbreviations, `ABT`/`BEF`/`AFT`/`BET`); 99.7%
  parse. The rest are mostly alternatives "22 AUG 1892 OR 25 AUG 1892" and day-month with
  no year. 8 Julian dates, no dual dating.
- **The data is mostly recent:** median event year 1895, 90th percentile 1949, a few into
  the 2000s (living people may be present). There are a few typo years (150, 2977).
- Fill rates: birth 50% of records (45% dated), baptism 24%, burial 9%, `CHR` almost never.
  `1 DEAT` is on **every** record but dated on only 14%: a bare `DEAT` just means
  "deceased". Marriage is on 96% of families, dated on 53%.
- `1 EVEN` on 73% of records is not a real event: mostly `TYPE ChildParent` (61k) and
  `EVEN LEGITIMATE_CHILD` (47k), leftovers of the software the trees were exported from.
  A few are meaningful (`BirthIlleg` 263, `Stillborn` 23, `Annulment` 33).

## Places
- Free-text `PLAC`, comma-separated, 1–9 levels; 11,519 distinct strings. The same place is
  written in many forms: "Meteghan, comté de Digby, Nouvelle-Écosse" vs
  "?, , , , CANADA, Meteghan, Nouvelle-Écosse".
- Filled on only 20–30% of events.
- `wt_places` is a per-tree place hierarchy; `wt_place_location` has coordinates for 74% of
  its rows. Both are unused so far but could standardise places.
- The most common places are in southwestern Nova Scotia (Sainte-Anne-du-Ruisseau,
  Wedgeport, Saulnierville, Meteghan, Pointe-de-l'Église), plus pre-Deportation Acadie
  (Port-Royal).

## Families
- At most one `FAMC` per person; `PEDI` is `birth` except 9 `adopted`.
- 61,681 families; 27,542 have no children (couple only), about 2,400 lack one spouse.
  8 same-sex and 13 unknown-sex couples are most likely entry errors.
- Families are small in each tree: in a sample of 3,000 people, the 2-hop family had a
  median of 11 people (max 106).

## Sources and notes
- 343,308 citations (`SOUR` links) to 7,537 sources. Sources are per tree (`@S12@` means
  nothing elsewhere), but 541 titles appear in several trees, so they can be compared by
  title. Most cited: Centre acadien's *Feuilles*, Bona Arsenault, the Sainte-Anne-du-Ruisseau
  register, Placide Gaudet, Stephen White's *Dictionnaire*.
- One "source", **"My Assumption, personnel du Centre acadien"** (12k citations), is the
  staff's own inference, not a document. Facts cited only to it are weaker.
- 117k notes in `wt_other`; unexplored.

## How much the trees overlap
- Less than one might expect. 19% of people have nobody in another tree with a compatible
  name (shared surname key and given name). Of the people with a birth year, only 4.9% have
  someone in another tree with exactly the same name and birth year.
- Real cross-tree duplicates exist but are a minority, so most candidate pairs are
  non-matches.

## Working with the export
- The Parquet export is read through an in-memory SQLite copy with the same SQL as MariaDB
  (`genealogie_acadienne.donnees.source_parquet`). SQLite compares text case-sensitively
  where MariaDB usually does not; WebTrees codes and xrefs are consistent, but tree names are
  not (`babin_test`).
- The SQL dump also contains WebTrees user and session tables: never publish it.
