"""Load the population every experiment starts from: a Parquet snapshot of the
real database, or the synthetic generator (same `Personne` objects either way)."""

from __future__ import annotations

from genealogie_acadienne import Personne
from genealogie_acadienne.commun.synthetique import generer_population
from genealogie_acadienne.donnees.instantane import lire_instantane

from .config import Config


def load_population(cfg: Config) -> list[Personne]:
    if cfg.data.source == "snapshot":
        return lire_instantane(cfg.data.snapshot_dir)
    if cfg.data.source == "synthetic":
        s = cfg.data.synthetic
        return generer_population(
            graine=cfg.seed, n_fondateurs=s.n_fondateurs, n_generations=s.n_generations,
            n_arbres=s.n_arbres, profondeur_arbre=s.profondeur_arbre,
        ).personnes
    raise ValueError(f"unknown data.source: {cfg.data.source!r} (use 'synthetic' or 'snapshot')")
