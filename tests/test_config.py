from pathlib import Path

import pytest

from acadian_er.config import config_from_dict, load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", sorted(p.name for p in (ROOT / "configs").glob("*.yaml")))
def test_every_config_loads(name):
    cfg = load_config(ROOT / "configs" / name)
    assert cfg.name and cfg.seed == 0


def test_unknown_key_is_an_error():
    with pytest.raises(ValueError, match=r"config.train.*epoch"):
        config_from_dict({"train": {"epoch": 3}})


def test_overrides_merge(tmp_path):
    cfg = load_config(ROOT / "configs" / "tiny_test.yaml", overrides={"train": {"epochs": 7}})
    assert cfg.train.epochs == 7 and cfg.train.batch_size == 64
