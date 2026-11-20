# Library staging

`src/acadian_er/lib_staging/` holds general-purpose code meant to move into
[`genealogie_acadienne`](https://github.com/Incandescent-Turtle/genealogie-acadienne).

Rules:
- French identifiers, following the library's conventions.
- Imports only `genealogie_acadienne`, the standard library and light dependencies:
  no project code, no torch, PyG or LLM code. `tests/lib_staging/test_frontiere.py`
  enforces this.
- Its own tests live in `tests/lib_staging/`: no DB, no project code.

Moving a module should be a copy: put the file in the destination, turn
`from genealogie_acadienne import X` into a relative import, and move its test file.

## Already moved (done in the library, `package-module` @ `93a34cf`)

These gaps were fixed directly in the library before this repo started:

| Change | Where in the library |
| --- | --- |
| `Proche.person_id`, `Mariage.conjoint_id`: relatives' xrefs, so the family graph can be built from `Personne` | `commun/modele.py`, `donnees/personnes.py` |
| `Personne.prenoms`, `nom_famille`, `noms_alternatifs` (from `wt_name`) | `commun/modele.py`, `donnees/personnes.py` |
| `Personne.dates`, `lieux`, `Mariage.date`, `lieu` from the raw GEDCOM; `evenements_gedcom` | `commun/gedcom.py`, `donnees/personnes.py` |
| `alias_dit`, `tokens_prenoms`, `trouver_paires`, taken from the unmerged `appariement-prenoms` branch (with a bug fix) | `commun/noms.py` |

## Staged modules

| Module | What it does | Intended destination | Changes needed when moving |
| --- | --- | --- | --- |
| `noms_variantes.py` | Canonical given names (variant table: Marie/Mary/Maria, Jean/John…); surname spelling keys (Comeau/Comeaux, Thibodeau/Thibodeaux, Arsenault/Arseneau, Melanson/Melançon…); dit aliases as alternative surnames | `commun/noms.py` (or `commun/variantes.py`) | Imports become relative (`.noms`). The tables (`GROUPES_PRENOMS`, `REGLES_NOM_FAMILLE`) should be reviewed by someone who knows the data; they are heuristics. |
| `candidats.py` | Relaxed-name blocking: index on (surname key, canonical given name) across all names, including alternative names; sex compatibility; tree exclusions | `commun/candidats.py`; `apparier_personnes.py` could use it instead of `trouver_noms_partages` | Depends on `noms_variantes` and `voisinage.Cle`. The library pipeline works on DataFrames; a DataFrame-level wrapper may be wanted. |
| `dates.py` | GEDCOM date parsing (ABT/EST/CAL/BEF/AFT/BET…AND/FROM…TO, dual dating, French month abbreviations); interval-aware year gaps; formatting; shifting | `commun/dates.py` | None. The library's `comparaison.py` could use `ecart_annees` to compare full dates instead of years. |
| `voisinage.py` | Typed family links from `Personne` (`parent_de`, `enfant_de`, `conjoint_de`); symmetrised link list; BFS neighbourhood within k hops; relatives by role (father, mother, spouses, children) | `commun/voisinage.py` | None. It would answer the library's own TODO about comparing beyond one generation. |
| `instantane.py` | Parquet snapshot export/import of `Personne` (node table with flattened facts, link table, manifest); `instantane_depuis_base(conn, dossier)` loads the whole DB (read-only) | `donnees/instantane.py` | Adds a `pyarrow` dependency to the library. `instantane_depuis_base` imports `charger_personnes`/`charger_groupe`; on moving, it becomes a relative import. Maybe add a `genealogie-instantane` entry point. |
| `synthetique.py` | Seeded synthetic multi-tree Acadian population: a "true" world of families across generations, rendered into overlapping trees with per-tree noise; returns `Personne` and the true identity of each record | `commun/synthetique.py` (pure) | Depends on `dates.MOIS_GEDCOM`. Its name and place pools and noise rates are assumptions (see DATA_MODEL.md). The library's tests could use it for larger fixtures. |

## Not staged, on purpose (project-specific)

- **Project-specific code:** the perturbation tiers and clone benchmark, the graph and
  features, the R-GCN, embeddings, RQ2 prompts, LLM backends and faithfulness, configs
  and evaluation.
- **`benchmark/clone.py`** (copying a family into another tree) is fairly general, but
  it exists only to build ground truth for this study. **Open question: move it, or keep
  it here?**
