# acadian-entity-resolution — agent guide

CISC 451 (Topics in Data Analytics, Queen's) course project. Duplicate detection
(entity resolution) in an Acadian genealogy database: ~150,000 people across ~60
WebTrees trees (MySQL/MariaDB, `wt_*` tables, GEDCOM-based).

Question: **when does the family-graph structure around a person help, compared
with that person's record alone?**
- **RQ1 (retrieval):** do R-GCN neighbourhood embeddings (k=1, 2 hops) rank the true
  duplicate higher than attribute-only methods? Ground truth by cloning + 5 perturbation tiers.
- **RQ2 (verification):** does an LLM given k=2 context verify a pair better than with k=0?
  Hand-labelled real pairs; precision/recall/F1 + faithfulness of cited evidence.

See `docs/RESEARCH_DESIGN.md` for the full design and `docs/ARCHITECTURE.md` for the code.

## Current state
- **No database access yet.** Everything runs on the synthetic generator
  (`genealogie_acadienne.commun.synthetique`), which feeds the same pipeline as a real snapshot.
- Scaffold only: no tuning, no real training runs. Sensible defaults.

## Commands
```bash
# setup (Windows, GTX 1070): torch from the cu126 index FIRST, then the project
python -m venv .venv && .venv\Scripts\activate
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
pip install -e ".[dev]"

pytest                                                   # all tests, CPU, < 1 min
acadian-er rq1 --config configs/dev_synthetic.yaml       # RQ1 end to end on synthetic data
acadian-er rq2-synthetic --config configs/dev_synthetic.yaml
acadian-er snapshot --config configs/rq1_webtrees.yaml   # needs .env and DB access
```
Stages: `snapshot synth benchmark train evaluate rq1 rq2-candidates rq2 rq2-synthetic`
(see `docs/EXPERIMENTS.md`).

## Rules
- **Never commit data or `.env`.** `data/`, `results/`, `temp/`, checkpoints are gitignored.
  `temp/` holds old name-only exports from the library repo: do not read or use them.
- **No real data in tests.** Tests use the synthetic generator or hand-built `Personne`
  objects only; they block the network and unset `DB_*`.
- **Experiments must be reproducible:** seeded (`Config.seed`) and config-driven (YAML in
  `configs/`; unknown keys are errors). Every run writes `config.yaml` + `manifest.json`
  (git commit, seed) next to its results.
- No hyperparameter tuning until real data is available; keep defaults sensible.
- Commits: small, focused, short human titles, minimal bullet bodies. The user is the
  only author: no co-author / attribution trailers.
- Where we guess about the real data, say so in `docs/DATA_MODEL.md`, not only in code.

## The library: `genealogie_acadienne`
Required dependency (French), the user's own repo, checked out next to this one at
`../genealogie-acadienne`, branch `package-module`; pinned in `pyproject.toml` to a commit.
Use it for:
- DB connection and loading (`DBConfig`, `get_connection`, `charger_personnes`,
  `charger_groupe`) and the `Personne` model;
- exact-name pooling (`trouver_noms_partages`, `trouver_paires`) and pairwise
  comparison (`comparer`, `criteres_concordants`);
- the tools that started here and moved there:
  - `commun.variantes`, `commun.candidats`, `commun.dates`;
  - `commun.voisinage`, `commun.clonage`, `commun.synthetique`;
  - `donnees.instantane` (Parquet snapshots).
- Import it directly. No optional imports, no try/except fallbacks, no copies or
  reimplementations of what it does. We convert `Personne` into graphs/tensors; we never
  define a competing person model.
- If the library is missing something general, propose fixing it **there** (the user
  agreed to edit and push `package-module`), then bump the pin here.

## Library staging rules (`src/acadian_er/lib_staging/`)
Waiting area for new general-purpose code that should later move into
`genealogie_acadienne` (currently empty; the user approves each move, which is a copy
into the library, a push to `package-module`, and a pin bump here):
- one module per concern, **French identifiers** (English docstrings OK), following the
  library's conventions (`Personne`, `charger_*`, DB access through its `run_query`/`t`);
- may import only `genealogie_acadienne`, the standard library and light deps
  (pandas, pyarrow, numpy); **never** the rest of `acadian_er`, torch, PyG or LLM code
  (enforced by `tests/lib_staging/test_frontiere.py`);
- its own tests in `tests/lib_staging/`, with no DB and no project code;
- every module listed in `docs/LIBRARY_STAGING.md` (purpose, destination, what changes on move).
- **When unsure whether something is general or project-specific, ask the user.**

## Where things live
| Path | What |
| --- | --- |
| `src/acadian_er/lib_staging/` | waiting area for library-bound code (empty; see `docs/LIBRARY_STAGING.md`) |
| `src/acadian_er/graph/` | Personne -> features + typed edges (PyG), k-hop ego batches |
| `src/acadian_er/benchmark/` | cloning, perturbation tiers, labelled RQ1 queries |
| `src/acadian_er/baselines/` | exact-name + criteria (old method), TF-IDF, sentence-transformer |
| `src/acadian_er/model/` | R-GCN encoder, augmentations, contrastive training |
| `src/acadian_er/evaluation/` | Recall@K, MRR, report tables |
| `src/acadian_er/rq2/` | contexts, prompt, LLM backends, parsing, faithfulness, metrics, labels |
| `src/acadian_er/experiments/` | stage functions used by the CLI and smoke tests |
| `configs/` | experiment YAML (`tiny_test` for tests, `dev_synthetic`, real-data configs) |
| `docs/` | architecture, research design, data model, experiments, hardware, staging, ADRs |
