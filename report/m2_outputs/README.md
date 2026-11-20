# Milestone 2 outputs and how they were produced

All runs on 2026-11-20, project commit `8ee8b10`, library `genealogie-acadienne`
`package-module` at `58f6445`, seed 0, GTX 1070. Each run folder keeps the exact
`config.yaml` and `manifest.json` written by the pipeline.

| Report item | Source here | Produced by |
| --- | --- | --- |
| Table 1 (dataset), Data section numbers | `dataset_stats.txt` | `scripts/stats.py` on the snapshot below + `temp/noms_partages.csv`, `partages_resume.csv`, `paires_exact.csv` |
| Data-quality counts (~5,200 flagged fields) | `temp/erreurs_a_corriger.txt` (summary at top) | library `trouver_erreurs`, run earlier on the full DB |
| Criteria-method results (2,545 pairs, 95.5% relational) | `derived_numbers.txt` | counted from `temp/correspondances_3.md` (library criteria solver, run earlier on the full DB over the 596,666 exact-name pairs; that version still had the `periode_estimee` criterion) |
| Table 2 (RQ1, real records, attribute-only) | `real_attributes/` | see "Real-attribute run" |
| t1 breakdown by perturbation type, t0 ties | `derived_numbers.txt` | computed from the real run's `per_query.csv` |
| Table 3 (RQ1, synthetic, depth 1) | `synthetic_depth1/` | `acadian-er rq1 --config configs/dev_synthetic.yaml` |
| Depth-2 sentence | `synthetic_depth2/` | `acadian-er rq1 --config configs/dev_synthetic_depth2.yaml` |

## Real-attribute run

The CSV export `temp/genealogy_master.csv` (tree_id, person_id, clean_name, raw_birth:
149,594 rows, 41 duplicated keys → 149,553 people) has names and birth events only:
no sex, no family links. It was converted with a throw-away script (not in the repo,
because the real input will be a DB snapshot):

```
python scripts/load_master.py temp/genealogy_master.csv <snapshot_dir>
acadian-er rq1 --config scripts/real_attributes.yaml   # after fixing its absolute paths
```

- `load_master.py`: parses DATE / PLAC out of the flattened GEDCOM birth string, takes
  the upper-case word(s) as surname when present, sex = unknown, writes a library
  Parquet snapshot.
- `real_attributes.yaml`: 500 anchors with given name + surname + birth year
  (`min_fields: 3`, `min_family: 0`), tiers t0–t2 only, methods exact_name, tfidf,
  sentence_transformer, rgcn_k0; Recall@1/5/10 and MRR. Total runtime ~3 min.

Caveats to state in the report (already written in): no sex filter on candidates; the
exact_name baseline can only use birth criteria here; 114/500 t1 queries had no possible
name perturbation; R-GCN was trained only at k=0 (no edges).
