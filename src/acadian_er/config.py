"""Experiment configuration: YAML files -> typed dataclasses.

Every experiment is driven by one YAML file (see `configs/`). Unknown keys are
an error, so a typo never silently falls back to a default. `seed_everything`
seeds Python, NumPy and PyTorch from `Config.seed`.
"""

from __future__ import annotations

import dataclasses
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import yaml


@dataclass
class SyntheticConfig:
    n_fondateurs: int = 12
    n_generations: int = 5
    n_arbres: int = 6
    profondeur_arbre: int = 3


@dataclass
class DataConfig:
    source: str = "synthetic"            # "synthetic" | "snapshot"
    snapshot_dir: str = "data/snapshots/webtrees"
    synthetic: SyntheticConfig = field(default_factory=SyntheticConfig)


@dataclass
class BenchmarkConfig:
    out_dir: str = "data/benchmarks/default"
    n_anchors: int = 200                 # anchors per tier
    min_fields: int = 3                  # well-documented: dated facts + names present
    min_family: int = 3                  # well-documented: relatives present in the tree
    clone_depth: int = 1                 # 1 = immediate family (parents, spouses, children)
    clone_tree_base: int = 900           # clone trees are clone_tree_base + tier number
    tiers: list[str] = field(default_factory=lambda: [
        "t0_clean", "t1_name", "t2_dates", "t3_parent_names", "t4_neighbourhood", "t5_one_line"])
    date_shift_max: int = 5
    date_drop_prob: float = 0.5
    keep_fraction: float = 0.25          # tier 4: share of relatives kept


@dataclass
class FeatureConfig:
    given_dim: int = 128
    surname_dim: int = 64
    place_dim: int = 32
    year_center: float = 1750.0
    year_scale: float = 100.0


@dataclass
class ModelConfig:
    hidden_dim: int = 128
    out_dim: int = 64
    num_bases: int | None = None
    dropout: float = 0.1


@dataclass
class AugmentConfig:
    drop_given_prob: float = 0.3
    name_variant_prob: float = 0.2
    drop_fact_prob: float = 0.3
    shift_year_prob: float = 0.2
    shift_year_max: int = 3
    drop_place_prob: float = 0.3
    drop_edge_prob: float = 0.3


@dataclass
class TrainConfig:
    ks: list[int] = field(default_factory=lambda: [0, 1, 2])
    epochs: int = 10
    batch_size: int = 256
    anchors_per_epoch: int | None = 20_000   # None = every training node each epoch
    lr: float = 1e-3
    weight_decay: float = 1e-4
    temperature: float = 0.1
    device: str = "auto"                     # "auto" | "cpu" | "cuda"
    augment: AugmentConfig = field(default_factory=AugmentConfig)


@dataclass
class TextEmbeddingConfig:
    st_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    st_batch_size: int = 64
    st_device: str = "auto"


@dataclass
class RQ1Config:
    methods: list[str] = field(default_factory=lambda: [
        "exact_name", "tfidf", "sentence_transformer", "rgcn_k0", "rgcn_k1", "rgcn_k2"])
    recall_ks: list[int] = field(default_factory=lambda: [5, 10])


@dataclass
class BackendConfig:
    kind: str = "fake"                       # "fake" | "ollama" | "openai_compat"
    model: str = ""
    base_url: str = ""
    api_key_env: str | None = None           # name of the env var holding the key
    temperature: float = 0.0
    seed: int | None = 0
    timeout_s: float = 120.0
    json_mode: bool = True


@dataclass
class RQ2Config:
    backend: BackendConfig = field(default_factory=BackendConfig)
    ks: list[int] = field(default_factory=lambda: [0, 2])
    labels_path: str = "data/rq2/labelled_pairs.jsonl"
    candidates_out: str = "data/rq2/candidates_to_label.jsonl"
    candidate_method: str = "exact_name"     # RQ1 ranker used to propose pairs
    n_queries: int = 300
    top_n: int = 3
    max_pairs: int | None = None


@dataclass
class Config:
    name: str = "default"
    seed: int = 0
    results_dir: str = "results"
    data: DataConfig = field(default_factory=DataConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    text_embedding: TextEmbeddingConfig = field(default_factory=TextEmbeddingConfig)
    rq1: RQ1Config = field(default_factory=RQ1Config)
    rq2: RQ2Config = field(default_factory=RQ2Config)

    @property
    def run_dir(self) -> Path:
        return Path(self.results_dir) / self.name


def _build(cls: type, values: dict[str, Any] | None, where: str) -> Any:
    values = dict(values or {})
    hints = get_type_hints(cls)
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"unknown config key(s) in {where}: {sorted(unknown)}")
    kwargs = {}
    for name, value in values.items():
        hint = hints[name]
        if dataclasses.is_dataclass(hint):
            kwargs[name] = _build(hint, value, f"{where}.{name}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


def config_from_dict(values: dict[str, Any]) -> Config:
    return _build(Config, values, "config")


def load_config(path: str | os.PathLike, overrides: dict[str, Any] | None = None) -> Config:
    """Load a YAML config; `overrides` is merged on top (nested dicts merge)."""
    values = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if overrides:
        values = _merge(values, overrides)
    return config_from_dict(values)


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def config_to_dict(cfg: Config) -> dict[str, Any]:
    return dataclasses.asdict(cfg)


def seed_everything(seed: int) -> None:
    """Seed every RNG the project uses."""
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def resolve_device(name: str) -> str:
    import torch

    if name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return name


__all__ = [n for n in dir() if not n.startswith("_") and n not in {"annotations", "get_args", "get_origin"}]
