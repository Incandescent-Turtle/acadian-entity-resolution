import random

import pytest

from genealogie_acadienne.commun.clonage import choisir_bien_documentees, cloner_famille
from genealogie_acadienne.commun.voisinage import construire_adjacence, indexer, proches_par_role

from acadian_er.benchmark import TIERS, build_benchmark, load_benchmark, save_benchmark


@pytest.fixture
def setup(population, tiny_cfg):
    index = indexer(population)
    anchors = choisir_bien_documentees(index, 10, random.Random(0), 3, 3)
    return index, anchors, tiny_cfg.benchmark


def _clone(index, anchor, tree=900):
    fam, key = cloner_famille(anchor, index, tree, "C0_", 1, construire_adjacence(index))
    return {(p.tree_id, p.person_id): p for p in fam.values()}, key


def test_clone_is_self_contained(setup):
    index, anchors, _ = setup
    family, key = _clone(index, anchors[0])
    assert key == (900, "C0_0")
    for p in family.values():
        assert p.tree_id == 900
        for x in p.parents + p.enfants + p.conjoints:
            assert (900, x["person_id"]) in family
        for m in p.mariages:
            assert (900, m["conjoint_id"]) in family
    original = index[anchors[0]]
    assert family[key].nom_complet == original.nom_complet
    assert index[anchors[0]].tree_id != 900          # original untouched


def test_tiers(setup):
    index, anchors, bc = setup
    for anchor in anchors:
        for name, tier in TIERS.items():
            family, key = _clone(index, anchor)
            before = dict(family)
            what = tier(family, key, random.Random(1), bc)
            assert key in family and isinstance(what, str)
            a = family[key]
            if name == "t3_parent_names":
                roles = proches_par_role(a, indexer(family.values()))
                assert all(not q.nom_complet for q in roles["pere"] + roles["mere"])
                assert all(not x["nom"] for x in a.parents)
            if name == "t4_neighbourhood":
                assert len(family) - 1 <= int((len(before) - 1) * bc.keep_fraction)
            if name == "t5_one_line" and "kept" in what:
                roles = proches_par_role(a, indexer(family.values()))
                assert bool(roles["pere"]) != bool(roles["mere"])
            for p in family.values():     # references stay consistent after every tier
                for x in p.parents + p.enfants + p.conjoints:
                    assert (900, x["person_id"]) in family


def test_build_save_load(population, tiny_cfg, tmp_path):
    bench = build_benchmark(population, tiny_cfg, log=lambda *a: None)
    assert len(bench.queries) == len(bench.anchors) * len(tiny_cfg.benchmark.tiers)
    assert all(q.query[0] in bench.clone_trees for q in bench.queries)
    assert all(c[0] not in bench.clone_trees for q in bench.queries for c in q.candidates)
    assert sum(q.target_in_candidates for q in bench.queries) / len(bench.queries) > 0.8
    save_benchmark(bench, tmp_path / "b", tiny_cfg)
    again = load_benchmark(tmp_path / "b")
    assert again.queries == bench.queries and len(again.people) == len(bench.people)
    # same seed -> same benchmark
    assert build_benchmark(population, tiny_cfg, log=lambda *a: None).queries == bench.queries
