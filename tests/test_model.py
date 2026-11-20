import random

import numpy as np
import torch

from acadian_er.config import AugmentConfig
from acadian_er.graph import build_graph, ego_batch
from acadian_er.model import RGCNEncoder
from acadian_er.model.augment import augment
from acadian_er.model.train import embed, load_encoder, save_encoder, train_encoder


def test_encoder_k0_has_no_convolutions(population, tiny_cfg):
    g = build_graph(population, tiny_cfg.features)
    m0 = RGCNEncoder(g.encoder.dim, 3, 0, tiny_cfg.model)
    m2 = RGCNEncoder(g.encoder.dim, 3, 2, tiny_cfg.model)
    assert len(m0.convs) == 0 and len(m2.convs) == 2
    b = ego_batch(g, np.arange(8), 2)
    z = m2.eval()(g.data.x[b.node_ids], b.edge_index, b.edge_type, b.centre_pos)
    assert z.shape == (8, tiny_cfg.model.out_dim)
    assert torch.allclose(z.norm(dim=-1), torch.ones(8), atol=1e-5)


def test_augment_never_mutates_input(population):
    p = next(p for p in population if p.faits)
    before = repr(p)
    for s in range(20):
        augment(p, random.Random(s), AugmentConfig(drop_given_prob=1, drop_fact_prob=1))
    assert repr(p) == before


def test_training_is_seeded_and_saves(population, tiny_cfg, tmp_path):
    g = build_graph(population, tiny_cfg.features)
    a = train_encoder(g, 1, tiny_cfg, log=lambda *x: None)
    b = train_encoder(g, 1, tiny_cfg, log=lambda *x: None)
    assert a.history == b.history and len(a.history) == tiny_cfg.train.epochs
    keys = g.keys[:10]
    save_encoder(a, tmp_path / "m.pt", g.encoder.dim)
    again = load_encoder(tmp_path / "m.pt", tiny_cfg)
    assert np.allclose(embed(a, g, keys, tiny_cfg), embed(again, g, keys, tiny_cfg), atol=1e-6)
