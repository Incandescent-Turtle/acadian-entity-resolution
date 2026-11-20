import numpy as np
import pandas as pd

from genealogie_acadienne.commun.voisinage import indexer

from acadian_er.baselines import EmbeddingRanker, ExactNameCriteriaRanker, TfidfEncoder, record_text
from acadian_er.evaluation import rank_of_target, summarise


def test_record_text_is_attribute_only(population):
    p = next(p for p in population if p.parents and p.faits.get("BIRT"))
    text = record_text(p)
    assert p.nom_complet in text and str(p.faits["BIRT"]) in text
    assert not any(x["nom"] in text for x in p.parents if x["nom"] and x["nom"] != p.nom_complet)


def test_rankers_prefer_identical_record(population):
    people = indexer(population)
    keys = sorted(people)
    q, cands = keys[0], keys[:15]
    for ranker in (ExactNameCriteriaRanker(people), EmbeddingRanker(TfidfEncoder(), people, cands)):
        scores = ranker.score(q, cands)
        assert scores.shape == (15,) and scores[0] == scores.max()


def test_rank_ties_and_missing():
    cands = [(1, "a"), (1, "b"), (1, "c")]
    assert rank_of_target(np.array([0.9, 0.5, 0.1]), cands, (1, "b"), (9, "q")) == 2
    tied = [rank_of_target(np.array([1.0, 1.0, 1.0]), cands, (1, "b"), (9, "q"), seed=s) for s in range(20)]
    assert set(tied) <= {1, 2, 3} and len(set(tied)) > 1          # ties broken by seed, not order
    assert rank_of_target(np.array([1.0]), [(1, "a")], (1, "z"), (9, "q")) is None


def test_summarise():
    rows = pd.DataFrame({"method": ["m"] * 4, "tier": ["t1", "t1", "t2", "t2"],
                         "rank": pd.array([1, 6, None, 11], dtype="Float64"),
                         "n_candidates": [10, 10, 10, 12]})
    s = summarise(rows, [5, 10]).set_index("tier")
    assert s.loc["t1", "recall@5"] == 0.5 and s.loc["t1", "recall@10"] == 1.0
    assert s.loc["t1", "mrr"] == (1 + 1 / 6) / 2
    assert s.loc["t2", "candidate_recall"] == 0.5 and s.loc["t2", "mrr"] == (1 / 11) / 2
    assert s.loc["all", "n_queries"] == 4
