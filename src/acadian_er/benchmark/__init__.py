"""RQ1 ground truth by cloning: anchors + family copied into dummy trees
(`genealogie_acadienne.commun.clonage`), one perturbation tier per tree, each
clone labelled with its original."""

from .build import Benchmark, Query, build_benchmark, load_benchmark, save_benchmark
from .tiers import TIERS

__all__ = ["Benchmark", "Query", "build_benchmark", "load_benchmark", "save_benchmark",
           "TIERS"]
