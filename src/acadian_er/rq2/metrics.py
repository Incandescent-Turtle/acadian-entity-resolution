"""RQ2 metrics, per k.

Gold labels: match / not_match (unsure pairs excluded). Predictions: match /
not_match / insufficient / invalid. The positive class is "match":
  precision = TP / predicted match
  recall    = TP / gold match           (insufficient on a gold match is a miss)
  F1
plus decided_rate (share not insufficient/invalid), accuracy_on_decided,
invalid_rate, and faithfulness (share of citations supported; share of replies
with every citation supported).
"""

from __future__ import annotations

import pandas as pd


def verification_metrics(rows: pd.DataFrame) -> pd.DataFrame:
    """rows: one per (k, pair) with columns k, gold, verdict, n_cited, n_faithful."""
    out = []
    for k, g in rows.groupby("k"):
        g = g[g["gold"].isin(["match", "not_match"])]
        pred_match = g["verdict"] == "match"
        gold_match = g["gold"] == "match"
        tp = int((pred_match & gold_match).sum())
        precision = tp / int(pred_match.sum()) if pred_match.any() else 0.0
        recall = tp / int(gold_match.sum()) if gold_match.any() else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        decided = g["verdict"].isin(["match", "not_match"])
        correct = ((g["verdict"] == g["gold"]) & decided).sum()
        cited = int(g["n_cited"].sum())
        out.append({
            "k": int(k), "n_pairs": len(g), "n_gold_match": int(gold_match.sum()),
            "precision": precision, "recall": recall, "f1": f1,
            "decided_rate": float(decided.mean()) if len(g) else 0.0,
            "accuracy_on_decided": float(correct / decided.sum()) if decided.any() else 0.0,
            "invalid_rate": float((g["verdict"] == "invalid").mean()) if len(g) else 0.0,
            "citation_faithfulness": float(g["n_faithful"].sum() / cited) if cited else float("nan"),
            "fully_faithful_replies": float((g["n_faithful"] == g["n_cited"]).mean()) if len(g) else 0.0,
        })
    return pd.DataFrame(out)
