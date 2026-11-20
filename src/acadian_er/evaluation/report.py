"""Write result tables (CSV + Markdown) and a run manifest."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from ..config import Config, config_to_dict


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_manifest(cfg: Config, out_dir: Path, **extra) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.yaml").write_text(yaml.safe_dump(config_to_dict(cfg), sort_keys=False),
                                         encoding="utf-8")
    manifest = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "git_commit": git_commit(), "seed": cfg.seed, **extra}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def markdown_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = [format(v, floatfmt) if isinstance(v, float) else str(v) for v in r]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(summary: pd.DataFrame, per_query: pd.DataFrame, out_dir: Path, title: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_dir / "summary.csv", index=False)
    per_query.to_csv(out_dir / "per_query.csv", index=False)
    parts = [f"# {title}", ""]
    for tier, g in summary.groupby("tier", sort=False):
        parts += [f"## {tier}", "", markdown_table(g.drop(columns=["tier"])), ""]
    path = out_dir / "report.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
