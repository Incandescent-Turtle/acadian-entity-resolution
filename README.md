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

Status: a working, tested scaffold on **synthetic data**. There is no database access
yet, and nothing has been tuned.

## Setup

Python 3.13. On Windows with an NVIDIA GTX 1070 (Pascal, sm_61), PyTorch must come from
the **CUDA 12.6** wheel index (newer CUDA builds dropped Pascal). See
[docs/HARDWARE.md](docs/HARDWARE.md).

```bash
python -m venv .venv
.venv\Scripts\activate                     # macOS/Linux: source .venv/bin/activate
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
pip install -e ".[dev]"                    # also installs genealogie-acadienne (pinned commit)
pytest                                     # CPU only, under a minute
```

To develop against a local checkout of the library instead of the pinned commit:
`pip install -e ../genealogie-acadienne`.

For the real database, copy `.env.example` to `.env` and fill in the `DB_*` values.
LLM API keys go there too.

## Quickstart (synthetic data)

```bash
acadian-er rq1 --config configs/dev_synthetic.yaml            # benchmark -> train -> evaluate
cat results/dev_synthetic/rq1/report.md
acadian-er rq2-synthetic --config configs/dev_synthetic.yaml  # RQ2 with the fake LLM
cat results/dev_synthetic/rq2/report.md
```

`dev_synthetic` includes the sentence-transformer baseline, which downloads a ~470 MB
model on first use. Remove `sentence_transformer` from `rq1.methods` to skip it.

## With the real database

```bash
acadian-er snapshot --config configs/rq1_webtrees.yaml        # read-only export to data/snapshots/
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
