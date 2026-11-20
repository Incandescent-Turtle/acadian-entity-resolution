"""Self-supervised contrastive training (InfoNCE) and embedding.

For a batch of anchor people, two VIEWS are built: each node of each anchor's
k-hop ego graph gets an independently augmented record (`augment`), and family
links are dropped at random (`edge_drop_prob`). The encoder must map both views
of the same person close together and away from the other anchors in the batch
(in-batch negatives, symmetric InfoNCE). No labels are needed, so the same
training runs on the real database. Excluded nodes (benchmark anchors) are
never used as training anchors.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from genealogie_acadienne.commun.voisinage import Cle

from ..config import Config, resolve_device
from .augment import augment
from .rgcn import RGCNEncoder
from ..graph.build import RELATIONS, FamilyGraph
from ..graph.ego import EgoBatch, ego_batch


@dataclass
class TrainedEncoder:
    model: RGCNEncoder
    k: int
    history: list[float]


def _features(graph: FamilyGraph, batch: EgoBatch, rng: random.Random | None, cfg: Config) -> torch.Tensor:
    if rng is None:
        return graph.data.x[batch.node_ids]
    people = [augment(graph.people[i], rng, cfg.train.augment) for i in batch.node_ids.tolist()]
    return torch.from_numpy(graph.encoder.encode_many(people))


def _view(model, graph, centres, k, cfg, rng_py, rng_np, device):
    batch = ego_batch(graph, centres, k, cfg.train.augment.drop_edge_prob, rng_np)
    x = _features(graph, batch, rng_py, cfg).to(device)
    b = batch.to(device)
    return model(x, b.edge_index, b.edge_type, b.centre_pos)


def train_encoder(graph: FamilyGraph, k: int, cfg: Config, exclude: set[Cle] = frozenset(),
                  log=print) -> TrainedEncoder:
    """Train one encoder with `k` hops on `graph`, never using `exclude` as anchors."""
    tc = cfg.train
    device = resolve_device(tc.device)
    seed = cfg.seed * 100 + k
    torch.manual_seed(seed)
    rng_py, rng_np = random.Random(seed), np.random.default_rng(seed)

    model = RGCNEncoder(graph.encoder.dim, len(RELATIONS), k, cfg.model).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=tc.lr, weight_decay=tc.weight_decay)
    pool = np.array([i for i, key in enumerate(graph.keys) if key not in exclude], dtype=np.int64)
    history = []
    for epoch in range(tc.epochs):
        model.train()
        order = rng_np.permutation(pool)
        if tc.anchors_per_epoch:
            order = order[: tc.anchors_per_epoch]
        losses = []
        for start in range(0, len(order), tc.batch_size):
            centres = order[start:start + tc.batch_size]
            if len(centres) < 2:
                continue
            z1 = _view(model, graph, centres, k, cfg, rng_py, rng_np, device)
            z2 = _view(model, graph, centres, k, cfg, rng_py, rng_np, device)
            logits = z1 @ z2.T / tc.temperature
            target = torch.arange(len(centres), device=device)
            loss = (F.cross_entropy(logits, target) + F.cross_entropy(logits.T, target)) / 2
            optim.zero_grad()
            loss.backward()
            optim.step()
            losses.append(loss.item())
        history.append(float(np.mean(losses)) if losses else float("nan"))
        log(f"  k={k} epoch {epoch + 1}/{tc.epochs} loss {history[-1]:.4f}")
    return TrainedEncoder(model.cpu(), k, history)


@torch.no_grad()
def embed(enc: TrainedEncoder, graph: FamilyGraph, keys: list[Cle], cfg: Config,
          batch_size: int = 1024) -> np.ndarray:
    """L2-normalised embeddings of `keys` (no augmentation), in order."""
    device = resolve_device(cfg.train.device)
    model = enc.model.to(device).eval()
    idx = graph.idx(keys)
    out = []
    for start in range(0, len(idx), batch_size):
        batch = ego_batch(graph, idx[start:start + batch_size], enc.k)
        x = graph.data.x[batch.node_ids].to(device)
        b = batch.to(device)
        out.append(model(x, b.edge_index, b.edge_type, b.centre_pos).cpu().numpy())
    enc.model.cpu()
    return np.concatenate(out) if out else np.zeros((0, cfg.model.out_dim), dtype=np.float32)


def save_encoder(enc: TrainedEncoder, path: Path, in_dim: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": enc.model.state_dict(), "k": enc.k, "in_dim": in_dim,
                "history": enc.history}, path)
    path.with_suffix(".json").write_text(json.dumps({"k": enc.k, "history": enc.history}, indent=2))


def load_encoder(path: Path, cfg: Config) -> TrainedEncoder:
    blob = torch.load(path, map_location="cpu", weights_only=True)
    model = RGCNEncoder(blob["in_dim"], len(RELATIONS), blob["k"], cfg.model)
    model.load_state_dict(blob["state_dict"])
    return TrainedEncoder(model, blob["k"], list(blob["history"]))
