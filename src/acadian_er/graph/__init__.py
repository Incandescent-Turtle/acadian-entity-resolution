"""Family graph: Personne -> node features + typed edges (PyG), and k-hop ego batches."""

from .build import RELATIONS, FamilyGraph, build_graph
from .ego import EgoBatch, ego_batch
from .features import FeatureEncoder

__all__ = ["RELATIONS", "FamilyGraph", "build_graph", "EgoBatch", "ego_batch", "FeatureEncoder"]
