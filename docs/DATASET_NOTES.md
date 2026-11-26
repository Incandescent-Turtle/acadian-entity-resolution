# Notes on the Acadian WebTrees dataset

Practical notes on the dataset itself, for anyone who works with it: traps, quirks, and
what turned out *not* to be useful. They do not depend on any code that uses the data.

**Read this before** loading, filtering, counting or matching people in this data, choosing
which trees to use, or drawing conclusions from it. **Add to it** when you find a new quirk
of the data. Keep it about the data only: no project code, methods or results.

All numbers were measured directly on the tables of the dump `webtree-testing.sql`
(MariaDB, 317 MB, sha256 `e050c18a6d4b8a90…`) in November 2026. A newer dump may differ;
the checks at the end show how to verify the most important points.

## What it is
- One WebTrees install, 69 trees (`wt_gedcom`) with 149,553 individuals. Most trees are named
  after a family (COMEAU, LEBLANC, DOUCET…) and are maintained separately, so the same
  person can appear in several of them. Sizes range from 41 to 10,627 people (median 1,100).
- Tables: `wt_individuals` (one GEDCOM record per person, in `i_gedcom`), `wt_name`,
  `wt_families`, `wt_link` (every xref reference: FAMC, FAMS, CHIL, HUSB, WIFE, SOUR, NOTE,
  REPO), `wt_dates`, `wt_places`, `wt_place_location`, `wt_sources`, `wt_other` (notes,
  repositories). `wt_media` is empty.
- `person_comparisons` is not a WebTrees table. It was added later and holds 29,980 pairs of
  people from different trees with the same name, each with the facts they agree on.
- xrefs (`@I123@`) are only unique **within** a tree; always key people by
  `(tree id, xref)`.
- The dump also contains WebTrees user and session tables: never publish it.

## Trees to exclude
| id | Tree | People | Why |
| --- | --- | --- | --- |
| 71 | `FAMILLES.ACADIENNES` | 6,910 | Copy of AMIRAULT + BABIN + ALLAIN (4,515 + 1,912 + 483, same `_UID`s). Imported from `Amirault__.ged`. |
| 72 | `babin_test` | 1,912 | Test copy of BABIN. Its name is lowercase in `wt_gedcom`, so case-sensitive filters miss it. |
| 70 | `MY_PROJECT` | 483 | Test project (from a Gramps export). |
| 39 | `HANKINSON` | 203 | **Wrong file imported.** Its `gedcom_filename` is `HARRINGTON_cleaned.ged`, and it holds the same 203 people as HARRINGTON (40), with the same xrefs and identical records. The real Hankinson tree is not in the database. Keep HARRINGTON. |
| -1 | `DEFAULT_TREE` | 0 | WebTrees placeholder. |

If HANKINSON is kept, every HARRINGTON person has a perfect duplicate; these are also the
201 pairs of `person_comparisons` whose two people share a `_UID`. Worth reporting to whoever
maintains the site.

## Identifiers that look useful but aren't
- **`_UID`** (non-empty on 65% of records): it does **not** link the same person across
  independently built trees. All 7,113 `_UID`s found in more than one tree come from the
  copied trees above; apart from those, no two trees share a `_UID`. It gives no ground truth
  for duplicates.
- **`REFN`**: a per-tree record counter (`1056`, `4416`…), not an identity.
- **`n_soundex_*`, `p_*_soundex`**: WebTrees' own phonetic codes, designed for English
  names. Nobody has checked how well they work on these French names.

## Names
- `wt_name.n_type` is always `NAME`: there are no `_MARNM` (married name) or `_AKA` rows.
  Only 41 people have two name rows. Alternative names live **inside** `n_full`.
- `n_givn` / `n_surn` are reliable: filled for 99.8%, and `n_givn` is always part of
  `n_full`. About a third of the trees write surnames in CAPITALS.
- 60% of people have one given name, 37% two, 3% three or more.
- **Dit names** (10.3% of names) are written after the surname as `dit` / `dite`:
  "Timothée COMEAU dit Tim", "Marie Léa Comeau dite Léa". They are the name the person went
  by (an aka), usually a form of one of their own given names (63%) or a nickname (26%: Harry,
  Joe, Hattie, l'aîné). Few are surnames. Another tree may know the person **only** by that
  name ("Tim Comeau", or no proper given name at all), so a dit is a possible given name.
  - 5% list several: "dit Alphée ou Alpheus", "dite soit Rosalie ou Rose Anne", "dit X dit Y".
  - Parentheses also carry alternatives: "Michel (Pierre) DUGAS", "Johnson (Jeanson)",
    "(dit Jasmin)". Question marks mark doubt ("McDcollt (?)").
- Expect English and French forms of the same name across trees (Marie/Mary, Henri/Harry)
  and surname spelling variants (Comeau/Comeaux, Doucet/Doucette).

## Dates and events
- Dates follow standard GEDCOM (English month abbreviations, `ABT`/`BEF`/`AFT`/`BET`). The few
  odd ones (0.3%) are mostly alternatives ("22 AUG 1892 OR 25 AUG 1892", "1706 OR 1707") or
  a day and month with no year. 8 Julian dates, no dual dating (1745/46).
- **The data is mostly recent:** median event year 1895, 90th percentile 1949, a few in the
  2000s (living people may be present). A few years are typos (150, 2977).
- Fill rates: birth on 50% of records (45% dated), baptism 24%, burial 9%, `CHR` almost
  never. `1 DEAT` is on **every** record but dated on only 14%: a bare `DEAT` just means
  "deceased". Marriage is on 96% of families, dated on 53%.
- `1 EVEN` on 73% of records is not a real event: mostly `TYPE ChildParent` (61k) and
  `EVEN LEGITIMATE_CHILD` (47k), leftovers of the software the trees were exported from.
  A few are meaningful (`BirthIlleg` 263, `Annulment` 33, `Stillborn` 23).

## Places
- Free-text `PLAC`, comma-separated, 1–9 levels; 11,519 distinct strings. The same place is
  written in many forms: "Meteghan, comté de Digby, Nouvelle-Écosse" vs
  "?, , , , CANADA, Meteghan, Nouvelle-Écosse".
- Filled on only 20–30% of events.
- `wt_places` is a per-tree place hierarchy; `wt_place_location` has coordinates for 74% of
  its rows. Both could help standardise places.
- The most common places are in southwestern Nova Scotia (Sainte-Anne-du-Ruisseau,
  Wedgeport, Saulnierville, Meteghan, Pointe-de-l'Église), plus pre-Deportation Acadie
  (Port-Royal).

## Families
- At most one `FAMC` per person; `PEDI` is `birth` except 9 `adopted`.
- 61,681 families; 27,542 have no children (couple only), about 2,400 lack one spouse.
  8 same-sex and 13 unknown-sex couples are most likely entry errors.
- Families are small in each tree: in a sample of 3,000 people, the family within two links
  (parents, children, spouses, and theirs) had a median of 11 people (max 106).

## Sources and notes
- 343,308 citations (`SOUR` links) to 7,537 sources. Sources are per tree (`@S12@` means
  nothing elsewhere), but 541 titles appear in several trees, so they can be compared by
  title. Most cited: Centre acadien's *Feuilles*, Bona Arsenault, the Sainte-Anne-du-Ruisseau
  register, Placide Gaudet, Stephen White's *Dictionnaire*.
- One "source", **"My Assumption, personnel du Centre acadien"** (12k citations), is the
  staff's own inference, not a document. Facts cited only to it are weaker.
- 117k notes in `wt_other`; unexplored.

## How much the trees overlap
Without the excluded trees (140,248 people):
- 46% of people have someone in another tree with exactly the same name, but of the people
  with a birth year, only 4.9% have someone with the same name **and** birth year.
- 19% have nobody in another tree sharing even a surname (allowing spelling variants and
  dits) and a given name.
- So real cross-tree duplicates exist but are a minority: most same-name pairs are different
  people (316 "Marie LeBlanc" in 42 trees).

## Checking a newer dump
- **Copied trees:** list `gedcom_filename` against `gedcom_name` in `wt_gedcom`, then count
  `_UID`s shared between each pair of trees (`1 _UID` lines of `i_gedcom`). A pair sharing
  hundreds of UIDs is a copy.
- **Name types:** `SELECT n_type, COUNT(*) FROM wt_name GROUP BY n_type`.
- **Dits:** `n_full LIKE '% dit %' OR n_full LIKE '% dite %'`.
- Tree names are not consistently cased (`babin_test`): compare them case-insensitively.
