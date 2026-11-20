"""Attribute features of ONE record (no relatives), as a fixed-size float vector.

Blocks (see `FeatureEncoder.blocks`):
  given    hashed canonical given names + their character trigrams (dit aliases included)
  surname  hashed character trigrams of the surname spelling key(s)
  sex      one-hot M / F / unknown
  years    for BIRT, BAPM, DEAT, BURI, first MARR: [present, scaled year]
  place    hashed tokens of the birth / baptism place

Relatives' names are deliberately NOT included: everything about the family
reaches the model only through graph edges, so k=0 is truly attribute-only.
Hashing uses CRC32 (stable across runs, unlike Python's `hash`).
"""

from __future__ import annotations

import zlib

import numpy as np

from genealogie_acadienne import Personne, normaliser
from genealogie_acadienne.commun.variantes import cles_noms_famille, cles_prenoms, nom_famille_probable

from ..config import FeatureConfig

YEAR_FACTS = ("BIRT", "BAPM", "DEAT", "BURI", "MARR")


def _h(text: str, dim: int) -> int:
    return zlib.crc32(text.encode("utf-8")) % dim


def _trigrams(token: str) -> list[str]:
    padded = f"#{token}#"
    return [padded[i:i + 3] for i in range(max(1, len(padded) - 2))]


def first_marriage_year(p: Personne) -> int | None:
    years = [m["annee"] for m in p.mariages if m.get("annee")]
    return min(years) if years else None


class FeatureEncoder:
    def __init__(self, cfg: FeatureConfig):
        self.cfg = cfg
        sizes = {"given": cfg.given_dim, "surname": cfg.surname_dim, "sex": 3,
                 "years": 2 * len(YEAR_FACTS), "place": cfg.place_dim}
        self.blocks: dict[str, slice] = {}
        start = 0
        for name, size in sizes.items():
            self.blocks[name] = slice(start, start + size)
            start += size
        self.dim = start

    def encode(self, p: Personne) -> np.ndarray:
        cfg, b = self.cfg, self.blocks
        v = np.zeros(self.dim, dtype=np.float32)
        surname = nom_famille_probable(p.nom_complet, p.nom_famille)

        given = v[b["given"]]
        for token in cles_prenoms(p.nom_complet, surname):
            given[_h("tok:" + token, cfg.given_dim)] += 1.0
            for g in _trigrams(token):
                given[_h("tri:" + g, cfg.given_dim)] += 0.5
        surn = v[b["surname"]]
        for key in cles_noms_famille(surname, p.nom_complet):
            for g in _trigrams(key):
                surn[_h(g, cfg.surname_dim)] += 1.0
        for block in ("given", "surname"):
            n = np.linalg.norm(v[b[block]])
            if n > 0:
                v[b[block]] /= n

        v[b["sex"].start + {"M": 0, "F": 1}.get(p.sexe, 2)] = 1.0

        years = v[b["years"]]
        for i, fact in enumerate(YEAR_FACTS):
            y = first_marriage_year(p) if fact == "MARR" else p.faits.get(fact)
            if y:
                years[2 * i] = 1.0
                years[2 * i + 1] = (y - cfg.year_center) / cfg.year_scale

        place = v[b["place"]]
        for fact in ("BIRT", "BAPM"):
            for token in normaliser(p.lieux.get(fact)).split():
                place[_h(token, cfg.place_dim)] = 1.0
        return v

    def encode_many(self, people: list[Personne]) -> np.ndarray:
        if not people:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self.encode(p) for p in people])
