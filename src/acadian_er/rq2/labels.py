"""Hand-labelled pairs: one JSON object per line (JSONL), kept under data/ (never committed).

  {"pair_id": "p0001",
   "tree_a": 12, "id_a": "I345", "tree_b": 40, "id_b": "I77",
   "label": "match" | "not_match" | "unsure" | null,     # null = not labelled yet
   "labeller": "initials", "notes": "free text",
   "source": "exact_name top-3"}                           # how the pair was proposed

`unsure` pairs are kept but excluded from precision / recall.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

LABELS = ("match", "not_match", "unsure")


@dataclass
class LabelledPair:
    pair_id: str
    tree_a: int
    id_a: str
    tree_b: int
    id_b: str
    label: str | None = None
    labeller: str = ""
    notes: str = ""
    source: str = ""

    @property
    def a(self) -> tuple[int, str]:
        return self.tree_a, self.id_a

    @property
    def b(self) -> tuple[int, str]:
        return self.tree_b, self.id_b


def read_labels(path: str | Path) -> list[LabelledPair]:
    pairs = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("label") not in (*LABELS, None):
            raise ValueError(f"{path}:{n}: label must be one of {LABELS} or null, got {d.get('label')!r}")
        pairs.append(LabelledPair(**{**d, "tree_a": int(d["tree_a"]), "tree_b": int(d["tree_b"]),
                                     "id_a": str(d["id_a"]), "id_b": str(d["id_b"])}))
    return pairs


def write_labels(pairs: list[LabelledPair], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
    return path
