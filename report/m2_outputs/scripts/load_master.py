"""TEMPORARY (Milestone 2 only): convert temp/genealogy_master.csv into a library
snapshot of attribute-only Personne records (name + birth date/place, no relatives).

Not part of the repo: the real data will come from the DB via `acadian-er snapshot`.
Usage: python load_master.py <csv> <snapshot_out_dir>
"""
import re
import sys

import pandas as pd

from genealogie_acadienne import Personne, normaliser
from genealogie_acadienne.commun.dates import annee
from genealogie_acadienne.donnees.instantane import ecrire_instantane

# raw_birth is a flattened GEDCOM fragment: "1 BIRT 2 DATE ABT 1674 2 PLAC Acadie, Port-Royal 2 ADDR ..."
TAG = r"(?=\s+\d\s+[A-Z_]{3,5}\b|\s*$)"
DATE = re.compile(r"\b2\s+DATE\s+(.*?)" + TAG)
PLAC = re.compile(r"\b2\s+PLAC\s+(.*?)" + TAG)


def split_name(full: str) -> tuple[str, str]:
    """Surnames are upper-case in most exports ('Claude BOURGEOIS'); else leave it to the library."""
    base = re.split(r"\s+dite?\s+", full)[0].split()
    caps = [w for w in base if len(w) > 1 and w.isupper()]
    if caps:
        i = base.index(caps[0])
        return " ".join(base[:i]), " ".join(caps)
    return "", ""


def to_personne(row) -> Personne:
    full = str(row.clean_name) if isinstance(row.clean_name, str) else ""
    given, surname = split_name(full)
    raw = row.raw_birth if isinstance(row.raw_birth, str) else ""
    d, pl = DATE.search(raw), PLAC.search(raw)
    date = d.group(1).strip() if d else None
    place = pl.group(1).strip() if pl else None
    faits, dates, lieux = {}, {}, {}
    if date or place:
        faits["BIRT"] = annee(date)
        dates["BIRT"], lieux["BIRT"] = date, place
    return Personne(tree_id=int(row.tree_id), person_id=str(row.person_id), nom_complet=full,
                    nom_norm=normaliser(full), sexe="U", faits=faits, prenoms=given,
                    nom_famille=surname, dates=dates, lieux=lieux)


def main(csv: str, out: str) -> None:
    df = pd.read_csv(csv, encoding="utf-8", dtype={"person_id": str})
    people = [to_personne(r) for r in df.itertuples(index=False)]
    ecrire_instantane(people, out, source="genealogy_master.csv (attributes only, temporary)", graine=0)
    print(f"{len(people)} people from {df.tree_id.nunique()} trees -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
