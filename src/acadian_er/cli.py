"""Command line: `acadian-er <stage> --config configs/<file>.yaml`.

Stages
  snapshot        export the WebTrees database to a Parquet snapshot (needs .env; read-only)
  synth           write a synthetic population as a snapshot (same format)
  benchmark       RQ1: clone anchors, apply tiers, write labelled queries
  train           RQ1: train one R-GCN encoder per k in train.ks
  evaluate        RQ1: rank with every method in rq1.methods, write the report
  rq1             benchmark + train + evaluate
  rq2-candidates  RQ2: propose pairs to hand-label
  rq2             RQ2: verify labelled pairs with the configured LLM backend
  rq2-synthetic   RQ2 on synthetic ground-truth pairs (development only)
"""

from __future__ import annotations

import argparse
import warnings

from .config import load_config

STAGES = ("snapshot", "synth", "benchmark", "train", "evaluate", "rq1",
          "rq2-candidates", "rq2", "rq2-synthetic")


def main(argv: list[str] | None = None) -> None:
    warnings.filterwarnings("ignore", message=".*torch.jit.script.*", category=FutureWarning)
    parser = argparse.ArgumentParser(prog="acadian-er", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--config", required=True, help="YAML config file")
    parser.add_argument("--out", help="output directory (snapshot / synth only)")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.stage == "snapshot":
        from genealogie_acadienne import get_connection, load_env_file

        from genealogie_acadienne.donnees.instantane import instantane_depuis_base

        load_env_file()
        conn = get_connection()
        try:
            out = instantane_depuis_base(conn, args.out or cfg.data.snapshot_dir)
        finally:
            conn.close()
        print(f"snapshot written to {out}")
    elif args.stage == "synth":
        from genealogie_acadienne.donnees.instantane import ecrire_instantane
        from genealogie_acadienne.commun.synthetique import generer_population

        s = cfg.data.synthetic
        pop = generer_population(cfg.seed, s.n_fondateurs, s.n_generations, s.n_arbres,
                                 s.profondeur_arbre)
        out = ecrire_instantane(pop.personnes, args.out or cfg.data.snapshot_dir,
                                source=f"synthétique graine={cfg.seed}", graine=cfg.seed)
        print(f"{len(pop.personnes)} synthetic people written to {out}")
    elif args.stage in ("benchmark", "train", "evaluate", "rq1"):
        from .experiments import rq1

        {"benchmark": rq1.stage_benchmark, "train": rq1.stage_train,
         "evaluate": rq1.stage_evaluate, "rq1": rq1.run_rq1}[args.stage](cfg)
    elif args.stage == "rq2-candidates":
        from .experiments.rq2 import stage_candidates

        stage_candidates(cfg)
    elif args.stage == "rq2":
        from .experiments.rq2 import stage_verify

        stage_verify(cfg)
    elif args.stage == "rq2-synthetic":
        from .experiments.rq2 import stage_verify, synthetic_labelled_pairs

        people, pairs = synthetic_labelled_pairs(cfg, n=cfg.rq2.max_pairs or 40)
        stage_verify(cfg, people=people, pairs=pairs)


if __name__ == "__main__":
    main()
