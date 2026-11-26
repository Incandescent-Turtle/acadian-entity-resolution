"""Audit the real WebTrees data against the assumptions in docs/DATA_MODEL.md.

Reads the raw Parquet export (`data.parquet_dir`) and the Personne snapshot
(`data.snapshot_dir`) of a config and writes a Markdown report (default
`results/audit/audit.md`, gitignored). Real data only: not part of the tests.

    uv run python scripts/audit_real_data.py --config configs/rq1_webtrees.yaml
"""

from __future__ import annotations

import argparse
import gc
import json
import random
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd
from genealogie_acadienne.commun.candidats import IndexCandidats
from genealogie_acadienne.commun.clonage import score_documentation, taille_famille
from genealogie_acadienne.commun.dates import analyser_date
from genealogie_acadienne.commun.noms import alias_dit, normaliser
from genealogie_acadienne.commun.voisinage import (
    construire_adjacence,
    indexer,
    voisinage,
)
from genealogie_acadienne.donnees.instantane import lire_instantane, lire_manifeste
from genealogie_acadienne.donnees.noms import ARBRES_IGNORES

from acadian_er.config import load_config

SAMPLE = 3000  # people sampled for the slower per-person measures
FACTS = ("BIRT", "BAPM", "CHR", "DEAT", "BURI")


# --------------------------------------------------------------------- helpers
def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def table(rows: list[list], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + " --- |" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def dist(s: Any) -> str:
    s = pd.Series(s).dropna()
    if s.empty:
        return "n=0"
    q = s.quantile([0.5, 0.9, 0.99])
    return (f"n={len(s):,}, min {s.min():g}, median {q[0.5]:g}, p90 {q[0.9]:g}, "
            f"p99 {q[0.99]:g}, max {s.max():g}, mean {s.mean():.1f}")


def counts(s: pd.Series, n: int = 12) -> str:
    vc = pd.Series(s).value_counts(dropna=False)
    total = vc.sum()
    rows = [[repr(k), f"{v:,}", pct(v / total)] for k, v in vc.head(n).items()]
    if len(vc) > n:
        rows.append([f"… {len(vc) - n} more", f"{vc.iloc[n:].sum():,}", pct(vc.iloc[n:].sum() / total)])
    return table(rows, ["value", "count", "share"])


def gedcom_tag(texts: pd.Series, level: int, tag: str) -> pd.Series:
    """Value of the first `<level> <tag> value` line of each GEDCOM text (None if absent/empty)."""
    v = texts.str.extract(rf"(?m)^{level} {tag} ?(.*)$")[0].str.strip()
    return v.where(v != "")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# ------------------------------------------------------------------ raw tables
def audit_raw(pdir: Path, out: list[str]) -> pd.DataFrame:
    """Sections on the raw tables. Returns cross-tree `_UID` pairs for the snapshot part."""
    def rd(t: str, cols: list[str] | None = None) -> pd.DataFrame:
        return pd.read_parquet(pdir / f"{t}.parquet", columns=cols)

    trees = rd("wt_gedcom", ["gedcom_id", "gedcom_name"])
    ind = rd("wt_individuals", ["i_id", "i_file", "i_sex", "i_gedcom"])
    names = rd("wt_name", ["n_file", "n_id", "n_num", "n_type", "n_full", "n_givn", "n_surn"])
    fam = rd("wt_families", ["f_id", "f_file", "f_husb", "f_wife", "f_gedcom", "f_numchil"])
    links = rd("wt_link")
    tree_name = dict(zip(trees.gedcom_id, trees.gedcom_name))
    ignored_upper = {a.upper() for a in ARBRES_IGNORES}

    # 1. trees
    size = ind.i_file.value_counts()
    rows = [[t, tree_name.get(t, "?"), f"{n:,}", "yes" if str(tree_name.get(t, "")).upper() in ignored_upper else ""]
            for t, n in size.items()]
    out += ["## 1. Trees", (f"{len(size)} trees with people; {len(ind):,} individuals. "
            f"Library ignores {ARBRES_IGNORES} (compare case-insensitively: see the flag column)."),
            f"People per tree: {dist(size)}.", "",
            "<details><summary>All trees</summary>\n", table(rows, ["id", "name", "people", "ignored"]),
            "\n</details>", ""]

    # 2. names (assumptions 1-3)
    per_person = names.groupby(["n_file", "n_id"]).size()
    givn_tokens = names.n_givn.fillna("").str.split().str.len()
    surn_ph = names.n_surn.isin(["@N.M.", ""]) | names.n_surn.isna()
    givn_ph = names.n_givn.isin(["@P.N.", ""]) | names.n_givn.isna()
    full_has_givn = [normaliser(g) in normaliser(f) for g, f in zip(names.n_givn.fillna(""), names.n_full.fillna(""))]
    out += ["## 2. Names (assumptions 1–3)", "### n_type", counts(names.n_type), "",
            f"Name rows per person: {dist(per_person)}; people with >1 row: {(per_person > 1).sum():,}.", "",
            f"- empty/placeholder surname (`@N.M.`): {pct(surn_ph.mean())}; given (`@P.N.`): {pct(givn_ph.mean())}",
            f"- n_full contains n_givn (normalised): {pct(sum(full_has_givn) / len(names))}",
            "- given-name tokens in n_givn:", "", counts(givn_tokens, 8), ""]
    surname_case = names.n_surn.dropna()
    surname_case = surname_case[surname_case.str.len() > 1]
    out += [(f"- surname written in CAPITALS: {pct((surname_case == surname_case.str.upper()).mean())} "
            "(by tree convention; normalisation should hide it)"), ""]

    # dit names: where, how many, and whether the alias looks like a surname or a nickname
    full = names.n_full.fillna("")
    norm_full = full.map(normaliser)
    has_marker = norm_full.str.contains(r"\b(?:dit|dite|dits|dites)\b")
    marker = norm_full[has_marker].str.extract(r"\b(dit|dite|dits|dites)\b")[0]
    known_surnames = set(names.n_surn.dropna().map(normaliser)) - {""}
    kinds: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    sub = names[has_marker]
    for f, g, s in zip(sub.n_full, sub.n_givn.fillna(""), sub.n_surn.fillna("")):
        aliases = alias_dit(f)
        if not aliases:
            kind = "marker but no alias parsed"
        else:
            a = normaliser(aliases[0])
            givens = set(normaliser(g).split())
            if len(aliases) > 1:
                kind = "several aliases"
            elif a in givens or any(a.startswith(x[:3]) for x in givens if len(x) >= 3):
                kind = "nickname from own given names"
            elif a in known_surnames and a != normaliser(s):
                kind = "alias is a surname in the DB"
            else:
                kind = "other (nickname / unknown)"
        kinds[kind] += 1
        examples.setdefault(kind, []).append(f)
    marker_pos = []
    for f, s in zip(sub.n_full, sub.n_surn.fillna("")):
        nf, ns = normaliser(f), normaliser(s)
        m = re.search(r"\b(?:dit|dite|dits|dites)\b", nf)
        if ns and m:
            marker_pos.append("after surname" if nf.find(ns) != -1 and nf.find(ns) < m.start() else "before/without surname")
    rng = random.Random(0)
    out += ["### Dit names (assumption 1)",
            f"Name rows with a dit marker: {has_marker.sum():,} ({pct(has_marker.mean())}).", "",
            counts(marker), "", "Position of the marker:", "", counts(pd.Series(marker_pos)), "",
            "What the (first) alias looks like:", "",
            table([[k, f"{v:,}", pct(v / max(1, has_marker.sum())),
                    "; ".join(rng.sample(examples[k], min(4, len(examples[k]))))]
                   for k, v in kinds.most_common()], ["kind", "rows", "share", "examples"]), ""]
    punct = full.str.contains(r"[\"'()\[\]?,;*]")
    out += [(f"Name rows with quotes/brackets/?/commas: {punct.sum():,} ({pct(punct.mean())}); "
            f"examples: {'; '.join(full[punct].sample(min(8, punct.sum()), random_state=0))}"), ""]

    # 3. dates (assumption 4)
    date_lines = pd.concat([ind.i_gedcom, fam.f_gedcom]).str.extractall(
        r"(?m)^1 (BIRT|BAPM|CHR|DEAT|BURI|MARR)\n(?:[2-9] .*\n)*?2 DATE (.*)$")
    date_lines.columns = ["fact", "date"]
    date_lines["date"] = date_lines.date.str.strip()
    parsed = date_lines.date.map(analyser_date)
    ok = parsed.notna()
    shape = date_lines.date[~ok].str.replace(r"\d", "9", regex=True).str.replace(r"[A-Za-zéû]{3,}", "W", regex=True)
    qual = parsed[ok].map(lambda d: d.qualificatif)
    months = date_lines.date.str.extract(r"\b([A-Za-zéû]{3,5})\.? \d{3,4}")[0].str.upper()
    out += ["## 3. Dates (assumption 4)",
            f"{len(date_lines):,} DATE lines on BIRT/BAPM/CHR/DEAT/BURI/MARR; parsed by `analyser_date`: {pct(ok.mean())}.", "",
            "Qualifiers of parsed dates:", "", counts(qual), "",
            "Unparsed shapes (digits→9, words→W):", "", counts(shape, 15), "",
            f"Unparsed examples: {'; '.join(date_lines.date[~ok].sample(min(12, (~ok).sum()), random_state=0))}", "",
            "Month tokens:", "", counts(months, 20), "",
            (f"Dual dating (1745/46): {date_lines.date.str.contains(r'\d{4}/\d').sum():,}. "
            f"Julian calendar in wt_dates: {(rd('wt_dates', ['d_type']).d_type == '@#DJULIAN@').sum()}."), ""]
    years = parsed[ok].map(lambda d: d.annee)
    out += [f"Years: {dist(years)}.", ""]

    # 4. facts present, places (assumption 5)
    rows = []
    for f in FACTS:
        has = ind.i_gedcom.str.contains(rf"(?m)^1 {f}\b")
        block = ind.i_gedcom.str.extract(rf"(?ms)(^1 {f}\b.*?)(?=^1 |\Z)")[0]
        rows.append([f, pct(has.mean()), pct(block.str.contains(r"(?m)^2 DATE").mean()),
                     pct(block.str.contains(r"(?m)^2 PLAC").mean())])
    mblock = fam.f_gedcom.str.extract(r"(?ms)(^1 MARR\b.*?)(?=^1 |\Z)")[0]
    rows.append(["MARR (families)", pct(fam.f_gedcom.str.contains(r"(?m)^1 MARR\b").mean()),
                 pct(mblock.str.contains(r"(?m)^2 DATE").mean()), pct(mblock.str.contains(r"(?m)^2 PLAC").mean())])
    other_events = ind.i_gedcom.str.findall(r"(?m)^1 ([A-Z_]{3,})").explode().value_counts()
    out += ["## 4. Facts and places (assumption 5)",
            table(rows, ["fact", "record has fact", "with DATE", "with PLAC"]), "",
            "All level-1 tags on individuals (share of records with ≥1):", "",
            table([[t, pct(ind.i_gedcom.str.contains(rf"(?m)^1 {t}\b").mean())] for t in other_events.head(25).index],
                  ["tag", "records"]), ""]
    plac = pd.concat([ind.i_gedcom, fam.f_gedcom]).str.findall(r"(?m)^2 PLAC (.*)$").explode().dropna().str.strip()
    plac_levels = plac.str.count(",") + 1
    places = rd("wt_places", ["p_id", "p_place", "p_parent_id", "p_file"])
    loc = rd("wt_place_location", ["place", "latitude", "longitude"])
    out += [f"PLAC values: {len(plac):,}, distinct {plac.nunique():,}; comma levels: {dist(plac_levels)}.",
            f"Most common: {'; '.join(f'{k} ({v:,})' for k, v in plac.value_counts().head(12).items())}.",
            (f"wt_places: {len(places):,} rows (per tree); wt_place_location: {len(loc):,} rows, "
            f"with coordinates {pct(loc.latitude.notna().mean())}."), ""]

    # 5. sex, 6. families (assumptions 6-7)
    famc = ind.i_gedcom.str.count(r"(?m)^1 FAMC ")
    pedi = ind.i_gedcom.str.findall(r"(?m)^2 PEDI (.*)$").explode().dropna()
    sex_by_id = {(f, i): s for f, i, s in zip(ind.i_file, ind.i_id, ind.i_sex)}
    couple_sex = Counter()
    for f, h, w in zip(fam.f_file, fam.f_husb, fam.f_wife):
        couple_sex[(sex_by_id.get((f, h), "-") if h else "-") + "/" + (sex_by_id.get((f, w), "-") if w else "-")] += 1
    chil = links[links.l_type == "CHIL"].groupby(["l_file", "l_from"]).size()
    out += ["## 5. Sex (assumption 6)", counts(ind.i_sex), "",
            "## 6. Families (assumption 7)", f"Families: {len(fam):,}.",
            "FAMC records per person:", "", counts(famc, 6), "", "PEDI values:", "", counts(pedi), "",
            "Couple sexes (HUSB/WIFE, '-' = missing):", "",
            table([[k, f"{v:,}"] for k, v in couple_sex.most_common(8)], ["HUSB/WIFE", "families"]), "",
            (f"Children per family (CHIL): {dist(chil)}; families with no children: "
            f"{len(fam) - len(chil):,}. FAMS per person: {dist(ind.i_gedcom.str.count(r'(?m)^1 FAMS '))}."),
            f"Link types: {', '.join(f'{k} {v:,}' for k, v in links.l_type.value_counts().items())}.", ""]

    # 7. _UID (assumption 8: overlap; possible real ground truth)
    uid = gedcom_tag(ind.i_gedcom, 1, "_UID")
    u = pd.DataFrame({"tree": ind.i_file, "pid": ind.i_id, "uid": uid}).dropna()
    per_uid_trees = u.groupby("uid").tree.nunique()
    per_uid_rows = u.groupby("uid").size()
    within = u.groupby(["uid", "tree"]).size()
    cross = u[u.uid.isin(per_uid_trees[per_uid_trees > 1].index)]
    pairs = cross.merge(cross, on="uid", suffixes=("_a", "_b"))
    pairs = pairs[pairs.tree_a < pairs.tree_b]
    tree_pairs = pd.DataFrame(pairs[["tree_a", "tree_b"]]).value_counts()
    ignored_ids = {t for t, n in tree_name.items() if str(n).upper() in ignored_upper}
    touching_ignored = (pairs.tree_a.isin(ignored_ids) | pairs.tree_b.isin(ignored_ids)).sum()
    refn = gedcom_tag(ind.i_gedcom, 1, "REFN")
    out += ["## 7. `_UID` across trees (assumption 8; possible real duplicates)",
            (f"Records with a non-empty `_UID`: {pct(uid.notna().mean())} ({uid.notna().sum():,}); "
            f"distinct values {len(per_uid_trees):,}."),
            (f"- UIDs in more than one tree: {(per_uid_trees > 1).sum():,}, covering {len(cross):,} records; "
            f"trees per such UID: {dist(per_uid_trees[per_uid_trees > 1])}."),
            f"- UIDs repeated inside one tree: {(within > 1).sum():,} (rows per UID overall: {dist(per_uid_rows)}).",
            f"- cross-tree pairs (one per tree pair per UID): {len(pairs):,}.",
            f"- UID format examples: {', '.join(uid.dropna().sample(3, random_state=0))}.",
            (f"- REFN: distinct {refn.nunique():,}, values look like {', '.join(refn.dropna().sample(5, random_state=0))} "
            "(per-tree counter, not an identity)."), "",
            "Top tree pairs by shared UIDs:", "",
            table([[f"{tree_name.get(a)} ({a})", f"{tree_name.get(b)} ({b})", f"{n:,}"]
                   for (a, b), n in cast(Any, tree_pairs.head(15).items())], ["tree A", "tree B", "shared UIDs"]), "",
            (f"Cross-tree UID pairs touching an ignored tree: "
            f"{touching_ignored:,}."),
            ""]

    # 8. sources
    sources = rd("wt_sources", ["s_id", "s_file", "s_name"])
    sour = links[links.l_type == "SOUR"]
    m = sour.merge(sources, left_on=["l_to", "l_file"], right_on=["s_id", "s_file"])
    trees_per_name = sources.groupby("s_name").s_file.nunique()
    out += ["## 8. Sources (not used yet)",
            (f"{len(sources):,} sources, {len(sour):,} SOUR links "
            f"({pct(sour.l_from.isin(ind.i_id).mean())} from individuals by xref)."),
            (f"Same source title in several trees: {(trees_per_name > 1).sum():,} titles "
            f"(max {trees_per_name.max()} trees)."), "",
            table([[k[:90], f"{v:,}"] for k, v in m.s_name.value_counts().head(10).items()], ["source", "citations"]), ""]

    # 9. person_comparisons (old method's pairs) vs UID pairs
    pc = rd("person_comparisons", ["tree_id_a", "person_id_a", "tree_id_b", "person_id_b", "n_criteria"])
    uid_set = {frozenset([(a, pa), (b, pb)]) for a, pa, b, pb in
               zip(pairs.tree_a, pairs.pid_a, pairs.tree_b, pairs.pid_b)}
    pc["uid_match"] = [frozenset([(a, pa), (b, pb)]) in uid_set for a, pa, b, pb in
                       zip(pc.tree_id_a, pc.person_id_a, pc.tree_id_b, pc.person_id_b)]
    by_n = pc.groupby("n_criteria").uid_match.agg(["size", "mean"])
    out += ["## 9. Old-method pairs (`person_comparisons`) against UID pairs",
            f"{len(pc):,} pairs; {pc.uid_match.sum():,} share a `_UID`.", "",
            table([[n, f"{int(r['size']):,}", pct(r['mean'])] for n, r in by_n.iterrows()],
                  ["n_criteria", "pairs", "share with same UID"]), ""]
    return pd.DataFrame(pairs[["tree_a", "pid_a", "tree_b", "pid_b"]]).reset_index(drop=True)


# -------------------------------------------------------------------- snapshot
def audit_snapshot(sdir: Path, uid_pairs: pd.DataFrame, cfg, out: list[str]) -> None:
    people = lire_instantane(sdir)
    index = indexer(people)
    adjacency = construire_adjacence(index)
    out += ["## 10. Snapshot", (f"{len(people):,} people, {len({k[0] for k in index})} trees "
            f"({lire_manifeste(sdir).get('cree_le')})."), ""]

    # field fill rates
    rows = [[f, pct(sum(1 for p in people if p.faits.get(f)) / len(people)),
             pct(sum(1 for p in people if p.lieux.get(f)) / len(people))] for f in FACTS]
    rows.append(["MARR (year)", pct(sum(1 for p in people if any(m.get("annee") for m in p.mariages)) / len(people)),
                 pct(sum(1 for p in people if any(m.get("lieu") for m in p.mariages)) / len(people))])
    out += ["### Field fill rates", table(rows, ["fact", "year", "place"]), "",
            (f"- prenoms filled: {pct(sum(1 for p in people if p.prenoms) / len(people))}; "
            f"nom_famille filled: {pct(sum(1 for p in people if p.nom_famille) / len(people))}; "
            f"noms_alternatifs non-empty: {sum(1 for p in people if p.noms_alternatifs):,}"), ""]

    # anchors (benchmark eligibility)
    score = pd.Series([score_documentation(p) for p in people])
    fam_size = pd.Series([taille_famille(p, index) for p in people])
    grid = [[mf] + [f"{((score >= mf) & (fam_size >= mfa)).sum():,}" for mfa in range(1, 7)] for mf in range(2, 7)]
    bc = cfg.benchmark
    out += ["### Anchor pool (`choisir_bien_documentees`)",
            f"Documentation score (0–7): {dist(score)}. Relatives in tree: {dist(fam_size)}.", "",
            "Eligible people by min_fields (rows) × min_family (columns):", "",
            table(grid, ["min_fields"] + [str(x) for x in range(1, 7)]), "",
            (f"Current config: min_fields={bc.min_fields}, min_family={bc.min_family} → "
            f"{((score >= bc.min_fields) & (fam_size >= bc.min_family)).sum():,} eligible for "
            f"n_anchors={bc.n_anchors}."), ""]

    # graph
    degree = pd.Series([len(adjacency.get(k, [])) for k in index])
    rng = random.Random(0)
    sample = rng.sample(sorted(index), min(SAMPLE, len(index)))
    hop1 = pd.Series([len(voisinage(k, index, 1, adjacency)) for k in sample])
    hop2 = pd.Series([len(voisinage(k, index, 2, adjacency)) for k in sample])
    out += ["### Family graph", f"Typed edges per person: {dist(degree)}; isolated: {pct((degree == 0).mean())}.",
            f"Neighbourhood size (sample of {len(sample):,}, incl. self): 1 hop {dist(hop1)}; 2 hops {dist(hop2)}.",
            f"Edge types: {', '.join(f'{k} {v:,}' for k, v in Counter(r for v in adjacency.values() for r, _ in v).items())}.", ""]

    # candidates: list sizes and blocking recall on UID pairs
    cand = IndexCandidats(people)
    lists = {k: cand.candidats(index[k]) for k in sample}
    sizes = pd.Series([len(v) for v in lists.values()])
    # overlap between trees (assumption 8): a candidate with the same name, and with the same
    # name and birth year (both known), as a rough upper/lower view of cross-tree duplicates
    exact = sum(any(index[c].nom_norm == index[k].nom_norm for c in v) for k, v in lists.items())
    known = [k for k in sample if index[k].faits.get("BIRT")]
    exact_birth = sum(any(index[c].nom_norm == index[k].nom_norm
                          and index[c].faits.get("BIRT") == index[k].faits.get("BIRT") for c in lists[k])
                      for k in known)
    in_snap = uid_pairs[[(a, b) in index and (c, d) in index for a, b, c, d in
                         zip(uid_pairs.tree_a, uid_pairs.pid_a, uid_pairs.tree_b, uid_pairs.pid_b)]]
    hits, n_checked, same_name, same_birth = 0, 0, 0, 0
    for a, pa, b, pb in in_snap.sample(min(SAMPLE, len(in_snap)), random_state=0).itertuples(index=False):
        p, q = index[(a, pa)], index[(b, pb)]
        n_checked += 1
        hits += (b, pb) in set(cand.candidats(p))
        same_name += p.nom_norm == q.nom_norm
        same_birth += bool(p.faits.get("BIRT")) and p.faits.get("BIRT") == q.faits.get("BIRT")
    out += ["### Candidates (`IndexCandidats`)",
            f"Candidates per person (sample): {dist(sizes)}; with none: {pct((sizes == 0).mean())}.",
            (f"Overlap (assumption 8): with a same-name candidate in another tree "
            f"{pct(exact / len(sample))}; of those with a birth year, same name and same year "
            f"{pct(exact_birth / max(1, len(known)))} (n={len(known):,})."),
            (f"Cross-tree UID pairs with both people in the snapshot: {len(in_snap):,}. "
            f"On {n_checked:,} sampled pairs:"),
            f"- partner in the candidate list (blocking recall): {pct(hits / max(1, n_checked))}",
            (f"- identical normalised name: {pct(same_name / max(1, n_checked))}; identical birth year: "
            f"{pct(same_birth / max(1, n_checked))}"), ""]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="results/audit/audit.md")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    pdir, sdir = Path(cfg.data.parquet_dir), Path(cfg.data.snapshot_dir)
    manifest = json.loads((pdir / "manifeste.json").read_text())
    out = ["# Real-data audit", "",
           (f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `scripts/audit_real_data.py` "
           f"(commit {git_commit()}, config `{args.config}`). Dump sha256 "
           f"`{str(manifest.get('source', {}).get('sha256', '?'))[:16]}…`."), ""]
    pairs = audit_raw(pdir, out)
    gc.collect()
    audit_snapshot(sdir, pairs, cfg, out)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")
    print(f"audit written to {path}")


if __name__ == "__main__":
    main()
