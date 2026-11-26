# Acadian entity resolution

Duplicate detection in an Acadian genealogy database (WebTrees, ~150,000 people in ~60
family trees). CISC 451 course project (Queen's University).

**When does the family graph around a person help, compared with the person's record alone?**

- **RQ1 — retrieval.** Do R-GCN family-neighbourhood embeddings (1 and 2 hops) rank the
  true duplicate higher than attribute-only methods? Known duplicates are made by cloning
  well-documented people into a dummy tree and perturbing them in five tiers.
- **RQ2 — verification.** Given a candidate pair, does an LLM decide match /
  not-match / not-enough-information better with the 2-hop family than with the two
  records alone, and is the evidence it cites really in its context?

Status: a working, tested scaffold. The real data is available as an offline Parquet
export of the WebTrees tables (`../data/parquet/`); experiments have only run on synthetic
data so far, and nothing has been tuned.

## Setup

Python 3.13 (pinned in `.python-version`), managed with [uv](https://docs.astral.sh/uv/).
`uv sync` picks the PyTorch build per platform: **CUDA 12.6** on Windows (the last line
with kernels for the GTX 1070, Pascal sm_61) and CPU-only on Linux. See
[docs/HARDWARE.md](docs/HARDWARE.md).

```bash
uv sync                                    # .venv + deps + genealogie-acadienne (pinned commit)
uv run pytest                              # CPU only, under a minute
```

Prefix commands with `uv run` (or activate `.venv`).

To develop against a local checkout of the library instead of the pinned commit:
`uv add --editable ../genealogie-acadienne`. Don't commit that change: push the library
and bump the pinned commit instead.

The real data is read from the Parquet export in `../data/parquet/` (`data.parquet_dir`).
To read a live WebTrees MariaDB instead, set `data.database: mariadb`, copy `.env.example`
to `.env` and fill in the `DB_*` values. LLM API keys go in `.env` too.

## Quickstart (synthetic data)

```bash
acadian-er rq1 --config configs/dev_synthetic.yaml            # benchmark -> train -> evaluate
cat results/dev_synthetic/rq1/report.md
acadian-er rq2-synthetic --config configs/dev_synthetic.yaml  # RQ2 with the fake LLM
cat results/dev_synthetic/rq2/report.md
```

`dev_synthetic` includes the sentence-transformer baseline, which downloads a ~470 MB
model on first use. Remove `sentence_transformer` from `rq1.methods` to skip it.

## With the real data

```bash
acadian-er snapshot --config configs/rq1_webtrees.yaml        # tables -> data/snapshots/webtrees/
acadian-er rq1 --config configs/rq1_webtrees.yaml
acadian-er rq2-candidates --config configs/rq2_ollama.yaml    # pairs to hand-label
acadian-er rq2 --config configs/rq2_ollama.yaml               # or configs/rq2_openai_compat.yaml
```

## Documentation

| | |
| --- | --- |
| [docs/RESEARCH_DESIGN.md](docs/RESEARCH_DESIGN.md) | RQ1 and RQ2, how they connect, threats to validity |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | modules, data flow, interfaces (diagram) |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | `Personne` -> graph and features; assumed vs confirmed |
| [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) | how to run each stage, where results go |
| [docs/HARDWARE.md](docs/HARDWARE.md) | PyTorch/CUDA for the GTX 1070, memory and timings |
| [docs/LIBRARY_STAGING.md](docs/LIBRARY_STAGING.md) | code destined for `genealogie_acadienne` |
| [docs/decisions/](docs/decisions/) | short ADRs for the design choices |

Depends on [`genealogie-acadienne`](https://github.com/Incandescent-Turtle/genealogie-acadienne)
(`package-module` branch) for database access, the `Personne` model, exact-name pooling
and pairwise comparison.
