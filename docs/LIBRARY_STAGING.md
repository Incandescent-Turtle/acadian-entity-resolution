# Library staging

`src/acadian_er/lib_staging/` is the waiting area for general-purpose code meant to
move into [`genealogie_acadienne`](https://github.com/Incandescent-Turtle/genealogie-acadienne).
**It is currently empty.** Everything staged so far has moved (see below).

Rules for a new staged module:
- French identifiers, following the library's conventions (`Personne`, `charger_*`,
  DB access through its `run_query` / `t`).
- Imports only `genealogie_acadienne`, the standard library and light dependencies
  (pandas, pyarrow, numpy): no project code, no torch, PyG or LLM code.
  `tests/lib_staging/test_frontiere.py` enforces this.
- Its own tests go in `tests/lib_staging/`: no DB, no project code.
- List it in the table at the end of this file: what it does, its destination, what
  changes on the move.
- When unsure whether something is general or project-specific, ask.

Moving a module is a copy:
1. put the file in its destination;
2. turn `from genealogie_acadienne import X` into a relative import;
3. move its tests;
4. export the public names;
5. bump the pin in `pyproject.toml`.

## Moved into the library

All changes are on `package-module`; this repo pins `58f6445`.

**Model gaps fixed directly in the library** (`f860afa`..`93a34cf`):

| Change | Where |
| --- | --- |
| `Proche.person_id`, `Mariage.conjoint_id`: relatives' xrefs, so the family graph can be built from `Personne` | `commun/modele.py`, `donnees/personnes.py` |
| `Personne.prenoms`, `nom_famille`, `noms_alternatifs` (from `wt_name`) | `commun/modele.py`, `donnees/personnes.py` |
| `Personne.dates`, `lieux`, `Mariage.date`, `lieu` from the raw GEDCOM; `evenements_gedcom` | `commun/gedcom.py`, `donnees/personnes.py` |
| `alias_dit`, `tokens_prenoms`, `trouver_paires`, from the unmerged `appariement-prenoms` branch, with a bug fix | `commun/noms.py` |

**Staged modules moved on 2026-11-20** (`c6a8b3f`..`58f6445`):

| Former staged module | Now | What it does | Follow-ups in the library |
| --- | --- | --- | --- |
| `noms_variantes.py` | `commun/variantes.py` | canonical given names (Marie/Mary…), surname spelling keys (Comeau/Comeaux…), dit aliases as alternative surnames | The tables (`GROUPES_PRENOMS`, `REGLES_NOM_FAMILLE`) are heuristics; review them against the real data. |
| `candidats.py` | `commun/candidats.py` | relaxed-name blocking (`IndexCandidats`) | `apparier_personnes.py` could use it instead of exact-name groups; it may want a DataFrame-level wrapper. |
| `dates.py` | `commun/dates.py` | GEDCOM date parsing, interval-aware gaps, formatting, shifting | `comparaison.py` could compare full dates with `ecart_annees`. |
| `voisinage.py` | `commun/voisinage.py` | typed family links, k-hop neighbourhood, relatives by role | Could answer `comparaison.py`'s TODO about comparing beyond one generation. |
| `benchmark/clone.py` (generic part) | `commun/clonage.py` | `score_documentation`, `taille_famille`, `choisir_bien_documentees`, `cloner_famille` | none |
| `synthetique.py` | `commun/synthetique.py` | seeded synthetic multi-tree Acadian population with true identities | Its name and place pools and noise rates are assumptions (DATA_MODEL.md). |
| `instantane.py` | `donnees/instantane.py` | Parquet snapshots; `instantane_depuis_base` (read-only DB export) | Added `pyarrow` to the library's dependencies. |

The perturbation tiers stay in this repo (`acadian_er.benchmark.tiers`) because they
are specific to the study.

## Currently staged

*(none)*
