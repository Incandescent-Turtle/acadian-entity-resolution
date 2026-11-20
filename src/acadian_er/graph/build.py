"""Build the relational family graph from Personne objects.

Nodes are people; edges are typed (`RELATIONS`: parent_of, child_of, spouse_of)
and always present in both directions (child_of is the inverse of parent_of),
which is what R-GCN expects. Edges never cross trees. The graph is stored as a
PyG `Data(x, edge_index, edge_type)` plus a CSR adjacency for fast ego batches.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch_geometric.data import Data

from genealogie_acadienne import Personne

from ..config import FeatureConfig
from ..lib_staging.voisinage import Cle, cle, indexer, tous_les_liens
from .features import FeatureEncoder

# lib_staging relation names -> project names (same order = relation ids)
RELATIONS = ("parent_of", "child_of", "spouse_of")
_FROM_STAGING = {"parent_de": 0, "enfant_de": 1, "conjoint_de": 2}


@dataclass
class FamilyGraph:
    keys: list[Cle]
    key_to_idx: dict[Cle, int]
    people: list[Personne]
    data: Data                       # x [N, F], edge_index [2, E], edge_type [E]
    rowptr: np.ndarray               # CSR over edges sorted by source
    col: np.ndarray
    etype: np.ndarray
    encoder: FeatureEncoder

    @property
    def num_nodes(self) -> int:
        return len(self.keys)

    def idx(self, keys: list[Cle]) -> np.ndarray:
        return np.array([self.key_to_idx[k] for k in keys], dtype=np.int64)


def build_graph(people: list[Personne], feature_cfg: FeatureConfig) -> FamilyGraph:
    index = indexer(people)
    keys = sorted(index)
    key_to_idx = {k: i for i, k in enumerate(keys)}
    ordered = [index[k] for k in keys]
    encoder = FeatureEncoder(feature_cfg)
    x = torch.from_numpy(encoder.encode_many(ordered))

    links = tous_les_liens(index)                      # sorted by source key
    src = np.array([key_to_idx[s] for s, _, _ in links], dtype=np.int64)
    dst = np.array([key_to_idx[d] for _, _, d in links], dtype=np.int64)
    typ = np.array([_FROM_STAGING[r] for _, r, _ in links], dtype=np.int64)
    order = np.lexsort((dst, src))
    src, dst, typ = src[order], dst[order], typ[order]
    rowptr = np.zeros(len(keys) + 1, dtype=np.int64)
    np.add.at(rowptr, src + 1, 1)
    rowptr = np.cumsum(rowptr)

    data = Data(x=x, edge_index=torch.from_numpy(np.stack([src, dst])),
                edge_type=torch.from_numpy(typ), num_nodes=len(keys))
    return FamilyGraph(keys, key_to_idx, ordered, data, rowptr, dst, typ, encoder)


__all__ = ["RELATIONS", "FamilyGraph", "build_graph", "cle"]
