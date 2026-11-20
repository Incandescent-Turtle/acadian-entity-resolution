"""Baseline: attribute-only text embeddings of a single record.

A record is written out as text (`record_text`) WITHOUT any relative, then
embedded by one of two encoders:

  TfidfEncoder                char 2-4-gram TF-IDF (default; deterministic,
                              no download, used in tests)
  SentenceTransformerEncoder  a pretrained multilingual sentence model
                              (downloaded once from Hugging Face; runs on the GPU)

Candidates are ranked by cosine similarity to the query.
"""

from __future__ import annotations

import numpy as np

from genealogie_acadienne import Personne
from genealogie_acadienne.commun.voisinage import Cle

from ..config import TextEmbeddingConfig, resolve_device
from .base import cosine_scores

FACT_LABELS = {"BIRT": "born", "BAPM": "baptised", "DEAT": "died", "BURI": "buried"}


def record_text(p: Personne) -> str:
    """e.g. 'Marie Louise Comeaux | female | born 12 MAR 1745 Grand-Pré, Acadie | died 1801 | married 1765'."""
    parts = [p.nom_complet or "(no name)",
             {"M": "male", "F": "female"}.get(p.sexe, "sex unknown")]
    parts += [f"also known as {n}" for n in p.noms_alternatifs]
    for fact, label in FACT_LABELS.items():
        date = p.dates.get(fact) or (str(p.faits[fact]) if p.faits.get(fact) else "")
        place = p.lieux.get(fact, "")
        if date or place:
            parts.append(" ".join(x for x in (label, date, place) if x))
    for m in p.mariages:
        when = m.get("date") or (str(m["annee"]) if m.get("annee") else "")
        if when or m.get("lieu"):
            parts.append(" ".join(x for x in ("married", when, m.get("lieu") or "") if x))
    return " | ".join(parts)


class TfidfEncoder:
    name = "tfidf"

    def encode(self, texts: list[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True,
                              lowercase=True, strip_accents="unicode")
        return vec.fit_transform(texts)     # rows L2-normalised (sparse)


class SentenceTransformerEncoder:
    name = "sentence_transformer"

    def __init__(self, cfg: TextEmbeddingConfig):
        self.cfg = cfg

    def encode(self, texts: list[str]) -> np.ndarray:
        # imported here only because loading transformers takes seconds
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.cfg.st_model, device=resolve_device(self.cfg.st_device))
        return model.encode(texts, batch_size=self.cfg.st_batch_size, normalize_embeddings=True,
                            show_progress_bar=False, convert_to_numpy=True)


class EmbeddingRanker:
    """Embeds every record that appears in a query or candidate list once, up front."""

    def __init__(self, encoder, people: dict[Cle, Personne], keys: list[Cle]):
        self.name = encoder.name
        keys = sorted(set(keys))
        matrix = encoder.encode([record_text(people[k]) for k in keys])
        if hasattr(matrix, "toarray"):           # sparse TF-IDF: keep rows sparse
            self._sparse = {k: matrix[i] for i, k in enumerate(keys)}
            self.embeddings = None
        else:
            self._sparse = None
            self.embeddings = {k: matrix[i] for i, k in enumerate(keys)}

    def score(self, query: Cle, candidates: list[Cle]) -> np.ndarray:
        if not candidates:
            return np.zeros(0)
        if self._sparse is not None:
            from scipy.sparse import vstack

            return (vstack([self._sparse[c] for c in candidates]) @ self._sparse[query].T).toarray().ravel()
        return cosine_scores(self.embeddings, query, candidates)
