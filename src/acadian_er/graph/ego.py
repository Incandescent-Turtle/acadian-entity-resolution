"""Batched k-hop ego subgraphs (our neighbour-sampled mini-batches).

Each centre gets its OWN copy of its k-hop family neighbourhood (a disjoint
union per batch), so a centre's embedding depends only on nodes within k hops,
exactly. Families are small (tens of nodes at k=2), so batches stay tiny even
on a 150k-node graph and fit easily in 8 GB.

Optional augmentation: `edge_drop` removes each undirected family link with
that probability (both directions together) before the k-hop walk.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .build import FamilyGraph


@dataclass
class EgoBatch:
    node_ids: torch.Tensor      # [n] global node index of each local node
    edge_index: torch.Tensor    # [2, e] local indices
    edge_type: torch.Tensor     # [e]
    centre_pos: torch.Tensor    # [b] local index of each centre

    def to(self, device: str) -> EgoBatch:
        return EgoBatch(self.node_ids.to(device), self.edge_index.to(device),
                        self.edge_type.to(device), self.centre_pos.to(device))


def _edges(graph: FamilyGraph, u: int, salt: int | None, edge_drop: float) -> np.ndarray:
    """Edge positions leaving `u`, minus dropped links. A link {u, v} is kept or
    dropped as a whole (same decision in both directions) from a salted hash."""
    positions = np.arange(graph.rowptr[u], graph.rowptr[u + 1])
    if salt is None:
        return positions
    v = graph.col[positions]
    a, b = np.minimum(u, v), np.maximum(u, v)
    h = ((a * 1_000_003 + b * 97 + salt) % 10_007) / 10_007.0
    return positions[h >= edge_drop]


def ego_batch(graph: FamilyGraph, centres: np.ndarray, k: int,
              edge_drop: float = 0.0, rng: np.random.Generator | None = None) -> EgoBatch:
    node_ids: list[int] = []
    src: list[int] = []
    dst: list[int] = []
    typ: list[int] = []
    centre_pos: list[int] = []
    salt = int(rng.integers(1 << 30)) if (rng is not None and edge_drop > 0) else None

    for c in centres.tolist():
        offset = len(node_ids)
        local = {c: 0}
        frontier = [c]
        for _ in range(k):
            nxt = []
            for u in frontier:
                for e in _edges(graph, u, salt, edge_drop):
                    v = int(graph.col[e])
                    if v not in local:
                        local[v] = len(local)
                        nxt.append(v)
            frontier = nxt
        members = list(local)
        if k > 0:
            for u in members:
                for e in _edges(graph, u, salt, edge_drop):
                    v = int(graph.col[e])
                    if v in local:
                        src.append(offset + local[u])
                        dst.append(offset + local[v])
                        typ.append(int(graph.etype[e]))
        node_ids.extend(members)
        centre_pos.append(offset)

    return EgoBatch(
        node_ids=torch.tensor(node_ids, dtype=torch.long),
        edge_index=torch.tensor([src, dst], dtype=torch.long).reshape(2, -1),
        edge_type=torch.tensor(typ, dtype=torch.long),
        centre_pos=torch.tensor(centre_pos, dtype=torch.long),
    )
