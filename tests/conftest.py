"""Project test fixtures. Rules: synthetic data only, CPU only, no network, no DB."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from acadian_er.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to open a network connection")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    for var in ("DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def tiny_cfg(tmp_path):
    """configs/tiny_test.yaml with every output redirected into tmp_path."""
    return load_config(ROOT / "configs" / "tiny_test.yaml", overrides={
        "results_dir": str(tmp_path / "results"),
        "benchmark": {"out_dir": str(tmp_path / "bench")},
        "rq2": {"candidates_out": str(tmp_path / "rq2" / "to_label.jsonl"),
                "labels_path": str(tmp_path / "rq2" / "labels.jsonl")},
    })


@pytest.fixture
def population(tiny_cfg):
    from acadian_er.data import load_population
    return load_population(tiny_cfg)
