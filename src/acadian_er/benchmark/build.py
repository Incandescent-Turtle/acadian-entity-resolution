"""Build, save and load the labelled RQ1 benchmark.

For each tier t: the SAME anchors are cloned into tree `clone_tree_base + t`,
the tier perturbation is applied, and a query is recorded:
(clone key -> original key, relaxed-name candidate list). All methods rank the
same candidate list. Candidates never include clone trees.

The benchmark is stored as a lib_staging snapshot of population + clones, plus
`queries.jsonl` and the config used.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from genealogie_acadienne import Personne

from ..config import Config
from ..lib_staging.candidats import IndexCandidats
from ..lib_staging.instantane import ecrire_instantane, lire_instantane
from ..lib_staging.voisinage import Cle, construire_adjacence, indexer
from .clone import clone_family, select_anchors
from .tiers import TIERS


@dataclass
class Query:
    tier: str
    query: Cle
    target: Cle
    candidates: list[Cle]
    perturbation: str

    @property
    def target_in_candidates(self) -> bool:
        return self.target in self.candidates


@dataclass
class Benchmark:
    people: list[Personne]          # population + all clones
    queries: list[Query]
    anchors: list[Cle]
    clone_trees: list[int]


def build_benchmark(population: list[Personne], cfg: Config, log=print) -> Benchmark:
    bc = cfg.benchmark
    rng = random.Random(cfg.seed)
    index = indexer(population)
    adjacency = construire_adjacence(index)
    anchors = select_anchors(index, bc.n_anchors, rng, bc.min_fields, bc.min_family)
    log(f"{len(anchors)} anchors selected from {len(index)} people")

    clones: list[Personne] = []
    pending: list[tuple[str, Cle, Cle, str]] = []
    clone_trees = []
    for t, tier in enumerate(bc.tiers):
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r} (choose from {sorted(TIERS)})")
        tree_id = bc.clone_tree_base + t
        clone_trees.append(tree_id)
        for n, anchor in enumerate(anchors):
            family, clone_key = clone_family(anchor, index, tree_id, prefix=f"C{n}_",
                                             depth=bc.clone_depth, adjacency=adjacency)
            family = {k_new: p for p in family.values() for k_new in [(p.tree_id, p.person_id)]}
            tier_rng = random.Random(f"{cfg.seed}:{tier}:{n}")
            what = TIERS[tier](family, clone_key, tier_rng, bc)
            clones.extend(family.values())
            pending.append((tier, clone_key, anchor, what))

    candidates_index = IndexCandidats(population)
    by_key = indexer(clones)
    queries = [
        Query(tier, q, target,
              candidates_index.candidats(by_key[q], arbres_exclus=clone_trees), what)
        for tier, q, target, what in pending
    ]
    covered = sum(q.target_in_candidates for q in queries)
    log(f"{len(queries)} queries; target in candidate list for {covered}/{len(queries)}")
    return Benchmark(population + clones, queries, anchors, clone_trees)


def save_benchmark(bench: Benchmark, out_dir: str | Path, cfg: Config) -> Path:
    out = Path(out_dir)
    ecrire_instantane(bench.people, out / "people", source=f"benchmark ({cfg.data.source})",
                      graine=cfg.seed, arbres_clones=bench.clone_trees)
    with open(out / "queries.jsonl", "w", encoding="utf-8") as f:
        for q in bench.queries:
            f.write(json.dumps(asdict(q), ensure_ascii=False) + "\n")
    meta = {"anchors": bench.anchors, "clone_trees": bench.clone_trees,
            "benchmark": asdict(cfg.benchmark), "seed": cfg.seed, "data_source": cfg.data.source}
    (out / "benchmark.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _key(x) -> Cle:
    return int(x[0]), str(x[1])


def load_benchmark(out_dir: str | Path) -> Benchmark:
    out = Path(out_dir)
    meta = json.loads((out / "benchmark.json").read_text(encoding="utf-8"))
    queries = []
    for line in (out / "queries.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        queries.append(Query(d["tier"], _key(d["query"]), _key(d["target"]),
                             [_key(c) for c in d["candidates"]], d["perturbation"]))
    return Benchmark(lire_instantane(out / "people"), queries,
                     [_key(a) for a in meta["anchors"]], meta["clone_trees"])
