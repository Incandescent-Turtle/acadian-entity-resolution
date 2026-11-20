"""R-GCN encoder whose number of message-passing layers IS the hop count k.

  x -> MLP -> h0 ; for each of k layers: h = LayerNorm(h + ReLU(RGCNConv(h))) ;
  embedding = normalize(Linear(h[centre]))

k = 0 has no convolution at all: the same model, attribute-only. That makes
"R-GCN k=0" the clean ablation of the graph (same features, same training).
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.nn import RGCNConv

from ..config import ModelConfig


class RGCNEncoder(nn.Module):
    def __init__(self, in_dim: int, num_relations: int, k: int, cfg: ModelConfig):
        super().__init__()
        self.k = k
        h = cfg.hidden_dim
        self.input = nn.Sequential(nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(cfg.dropout),
                                   nn.Linear(h, h))
        self.convs = nn.ModuleList(
            RGCNConv(h, h, num_relations, num_bases=cfg.num_bases, aggr="mean") for _ in range(k))
        self.norms = nn.ModuleList(nn.LayerNorm(h) for _ in range(k))
        self.dropout = nn.Dropout(cfg.dropout)
        self.output = nn.Linear(h, cfg.out_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_type: torch.Tensor,
                centre_pos: torch.Tensor) -> torch.Tensor:
        h = self.input(x)
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + self.dropout(F.relu(conv(h, edge_index, edge_type))))
        return F.normalize(self.output(h[centre_pos]), dim=-1)
