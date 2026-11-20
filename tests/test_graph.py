import copy

import numpy as np

from acadian_er.graph import RELATIONS, build_graph, ego_batch
from acadian_er.graph.features import FeatureEncoder
from acadian_er.lib_staging.voisinage import indexer, voisinage


def test_graph_shape_and_symmetry(population, tiny_cfg):
    g = build_graph(population, tiny_cfg.features)
    assert g.data.x.shape == (len(population), g.encoder.dim)
    ei, et = g.data.edge_index.numpy(), g.data.edge_type.numpy()
    edges = set(zip(ei[0], ei[1], et))
    inverse = {0: 1, 1: 0, 2: 2}
    assert all((d, s, inverse[t]) in edges for s, d, t in edges)
    assert set(et) <= set(range(len(RELATIONS)))


def test_features_ignore_relatives(population, tiny_cfg):
    enc = FeatureEncoder(tiny_cfg.features)
    p = next(p for p in population if p.parents)
    q = copy.deepcopy(p)
    q.parents, q.enfants, q.conjoints = [], [], []
    assert np.array_equal(enc.encode(p), enc.encode(q))


def test_ego_batch_matches_k_hop_neighbourhood(population, tiny_cfg):
    g = build_graph(population, tiny_cfg.features)
    index = indexer(population)
    centres = np.arange(0, g.num_nodes, 37)
    for k in (0, 1, 2):
        batch = ego_batch(g, centres, k)
        ids = batch.node_ids.numpy()
        bounds = list(batch.centre_pos.numpy()) + [len(ids)]
        for i, c in enumerate(centres):
            got = {g.keys[n] for n in ids[bounds[i]:bounds[i + 1]]}
            assert got == set(voisinage(g.keys[c], index, k))
            assert ids[bounds[i]] == c                      # centre first
        if k == 0:
            assert batch.edge_index.shape[1] == 0


def test_edge_drop_is_symmetric(population, tiny_cfg):
    g = build_graph(population, tiny_cfg.features)
    batch = ego_batch(g, np.arange(g.num_nodes)[:50], 1, edge_drop=0.5, rng=np.random.default_rng(0))
    ei = batch.edge_index.numpy()
    edges = set(zip(ei[0], ei[1]))
    assert all((d, s) in edges for s, d in edges)
