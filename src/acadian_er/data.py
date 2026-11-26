"""Load the population every experiment starts from: a Parquet snapshot of the
real database, or the synthetic generator (same `Personne` objects either way).

`build_snapshot` makes that snapshot from the WebTrees tables, read either from
the offline Parquet export (`data.parquet_dir`) or from a live MariaDB (`.env`).
Both go through the same library loaders."""

from __future__ import annotations

from pathlib import Path

from genealogie_acadienne import Personne
from genealogie_acadienne.commun.synthetique import generer_population
from genealogie_acadienne.donnees import ouvrir_connexion
from genealogie_acadienne.donnees.instantane import (
    instantane_depuis_base,
    lire_instantane,
    lire_manifeste,
)

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


def build_snapshot(cfg: Config, out: str | Path | None = None) -> Path:
    """Write the Personne snapshot (default `data.snapshot_dir`) from `data.database`."""
    if cfg.data.database not in ("parquet", "mariadb"):
        raise ValueError(f"unknown data.database: {cfg.data.database!r} (use 'parquet' or 'mariadb')")
    infos = {}
    if cfg.data.database == "parquet":
        # the export's manifest names the SQL dump it came from (file, sha256)
        infos["export"] = cfg.data.parquet_dir
        if (Path(cfg.data.parquet_dir) / "manifeste.json").is_file():
            infos["dump"] = lire_manifeste(cfg.data.parquet_dir).get("source")
    with ouvrir_connexion(cfg.data.parquet_dir if cfg.data.database == "parquet" else None) as conn:
        return instantane_depuis_base(conn, out or cfg.data.snapshot_dir,
                                      source=f"webtrees ({cfg.data.database})", **infos)
