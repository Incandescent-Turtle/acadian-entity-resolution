"""`acadian-er snapshot`: WebTrees tables (Parquet export) -> Personne snapshot.

Hand-built tables only (two people married in one family), no real data, no DB."""

from __future__ import annotations

import pandas as pd
import pytest
import yaml
from genealogie_acadienne.donnees.instantane import lire_instantane

from acadian_er.cli import main
from acadian_er.config import config_from_dict
from acadian_er.data import build_snapshot

TABLES = {
    "wt_gedcom": {"gedcom_id": [1], "gedcom_name": ["TEST"]},
    "wt_individuals": {"i_id": ["I1", "I2"], "i_file": [1, 1], "i_sex": ["M", "F"],
                       "i_gedcom": ["0 @I1@ INDI\n1 BIRT\n2 DATE 1700\n2 PLAC Grand-Pré",
                                    "0 @I2@ INDI"]},
    "wt_name": {"n_file": [1, 1], "n_id": ["I1", "I2"], "n_num": [0, 0],
                "n_type": ["NAME", "NAME"], "n_full": ["Jean /Babin/", "Marie /Léger/"],
                "n_givn": ["Jean", "Marie"], "n_surn": ["Babin", "Léger"]},
    "wt_families": {"f_id": ["F1"], "f_file": [1], "f_husb": ["I1"], "f_wife": ["I2"],
                    "f_gedcom": ["0 @F1@ FAM"]},
    "wt_link": {"l_file": [1, 1], "l_from": ["I1", "I2"], "l_type": ["FAMS", "FAMS"],
                "l_to": ["F1", "F1"]},
    "wt_dates": {"d_file": [1], "d_gid": ["I1"], "d_fact": ["BIRT"], "d_year": [1700]},
    "wt_places": {"p_id": [1], "p_file": [1], "p_place": ["Grand-Pré"]},
}


@pytest.fixture
def export(tmp_path):
    dossier = tmp_path / "parquet"
    dossier.mkdir()
    for table, colonnes in TABLES.items():
        pd.DataFrame(colonnes).to_parquet(dossier / f"{table}.parquet")
    return dossier


def test_snapshot_stage_from_parquet(tmp_path, export):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump({"name": "t", "data": {
        "source": "snapshot", "database": "parquet", "parquet_dir": str(export),
        "snapshot_dir": str(tmp_path / "snap")}}))
    main(["snapshot", "--config", str(cfg_path)])

    people = {p.person_id: p for p in lire_instantane(tmp_path / "snap")}
    assert set(people) == {"I1", "I2"}
    jean = people["I1"]
    assert jean.nom_complet == "Jean Babin" and jean.faits == {"BIRT": 1700}
    assert jean.lieux == {"BIRT": "Grand-Pré"}
    assert [c.get("person_id") for c in jean.conjoints] == ["I2"]


def test_unknown_database_is_an_error(tmp_path):
    cfg = config_from_dict({"data": {"database": "csv"}})
    with pytest.raises(ValueError, match="data.database"):
        build_snapshot(cfg, tmp_path / "snap")
