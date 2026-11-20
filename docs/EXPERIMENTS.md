# Running the experiments

Every command is `acadian-er <stage> --config <yaml>`. A run is fully defined by its
YAML file and `seed`. Outputs go to `results/<name>/`, and every output folder gets
`config.yaml` (the resolved config) and `manifest.json` (git commit, seed, timestamp).
`data/` and `results/` are gitignored.

| Config | Use |
| --- | --- |
| `configs/tiny_test.yaml` | the smoke tests (seconds, CPU) |
| `configs/dev_synthetic.yaml` | development on synthetic data (~42k people, 20 trees) |
| `configs/rq1_webtrees.yaml` | RQ1 on the real snapshot |
| `configs/rq2_ollama.yaml` | RQ2 with a local Ollama model |
| `configs/rq2_openai_compat.yaml` | RQ2 through OpenRouter or a cluster server |

## 0. Data

```bash
# real database (read-only; needs .env with DB_*)
acadian-er snapshot --config configs/rq1_webtrees.yaml      # -> data/snapshots/webtrees/
# or a synthetic population in the same format
acadian-er synth --config configs/dev_synthetic.yaml --out data/snapshots/synthetic
```

A snapshot folder has `personnes.parquet` (one row per person), `liens.parquet` (typed
links) and `manifeste.json`. Set `data.source: snapshot` and `data.snapshot_dir` to use
one. `data.source: synthetic` generates the population on the fly from `seed`.

## 1. RQ1 — retrieval

```bash
acadian-er benchmark --config configs/dev_synthetic.yaml    # anchors, clones, tiers, candidates
acadian-er train     --config configs/dev_synthetic.yaml    # one R-GCN per k in train.ks
acadian-er evaluate  --config configs/dev_synthetic.yaml    # every method in rq1.methods
# or all three:
acadian-er rq1       --config configs/dev_synthetic.yaml
```

| Output | Content |
| --- | --- |
| `benchmark.out_dir/people/` | snapshot of population + clones |
| `benchmark.out_dir/queries.jsonl` | tier, query, target, candidates, perturbation |
| `benchmark.out_dir/benchmark.json` | anchors, clone trees, settings |
| `results/<name>/rq1/checkpoints/rgcn_k{k}.pt` (+ `.json`) | encoder and loss history |
| `results/<name>/rq1/summary.csv`, `report.md` | Recall@5/@10, MRR, candidate recall per method × tier |
| `results/<name>/rq1/per_query.csv` | the target's rank for every method and query |

Choose methods with `rq1.methods`, from `exact_name`, `tfidf`, `sentence_transformer`
and `rgcn_k0|1|2`. The sentence-transformer model is downloaded from Hugging Face on
first use.

## 2. RQ2 — verification

```bash
# 1) propose pairs from an RQ1 ranker's top results on real data
acadian-er rq2-candidates --config configs/rq2_ollama.yaml   # -> data/rq2/candidates_to_label.jsonl
# 2) hand-label: set "label" to match / not_match / unsure, add labeller and notes,
#    save as data/rq2/labelled_pairs.jsonl (150–200 pairs)
# 3) verify with the LLM, k=0 and k=2
acadian-er rq2 --config configs/rq2_ollama.yaml
```

Labelled pair format (one JSON object per line):
```json
{"pair_id": "p0001", "tree_a": 12, "id_a": "I345", "tree_b": 40, "id_b": "I77",
 "label": "match", "labeller": "RM", "notes": "same parents, baptism 2 days apart",
 "source": "exact_name top-3"}
```

| Output (`results/<name>/rq2/`) | Content |
| --- | --- |
| `responses.jsonl` | per pair and k: verdict, cited evidence, unsupported citations, raw reply, prompt hash |
| `summary.csv`, `report.md` | precision, recall, F1, decided rate, accuracy on decided, invalid rate, faithfulness, per k |

Backends (`rq2.backend.kind`):
- `fake`: deterministic and offline; used by the tests and `rq2-synthetic`.
- `ollama`: e.g. `ollama pull qwen2.5:7b-instruct`, then point `model` at it.
- `openai_compat`: set `base_url`, `model` and `api_key_env`.
  - OpenRouter: `https://openrouter.ai/api/v1`.
  - A vLLM or llama.cpp server on a cluster: `http://<host>:<port>/v1`.

`acadian-er rq2-synthetic --config configs/dev_synthetic.yaml` runs RQ2 on synthetic
ground-truth pairs, to test prompts and backends before labelling real pairs. Never
report these numbers.

## Reproducibility checklist

- Change settings in a YAML file, not in code. Use a new `name` for each variant you
  want to keep.
- `seed` controls anchors, tiers, training, tie-breaking and the synthetic data.
- Pin the LLM model version in the config, and keep `responses.jsonl` (raw replies).
- `manifest.json` records the git commit. Commit before running an experiment you plan
  to report.
- GPU training is not bit-exact across hardware. Report the device (see HARDWARE.md).
