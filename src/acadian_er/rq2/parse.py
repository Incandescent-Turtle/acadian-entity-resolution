"""Parse an LLM reply into a 3-way verdict + cited evidence.

Tolerant of the usual noise: code fences, text around the JSON, verdict
synonyms ("same person", "no match", "unknown"...). An unparseable reply gets
verdict "invalid" (counted separately, never silently as a verdict).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

VERDICTS = ("match", "not_match", "insufficient")
_SYNONYMS = {
    "match": "match", "same": "match", "same person": "match", "yes": "match", "duplicate": "match",
    "not_match": "not_match", "not match": "not_match", "no match": "not_match",
    "different": "not_match", "no": "not_match", "nonmatch": "not_match", "non_match": "not_match",
    "insufficient": "insufficient", "not enough information": "insufficient",
    "not_enough_information": "insufficient", "unknown": "insufficient", "unsure": "insufficient",
    "cannot determine": "insufficient",
}


@dataclass
class Verdict:
    verdict: str                                   # match | not_match | insufficient | invalid
    evidence: list[dict] = field(default_factory=list)   # [{"id": ..., "value": ...}]
    rationale: str = ""
    error: str | None = None


def _first_json_object(text: str) -> dict | None:
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
        start = text.find("{", start + 1)
    return None


def parse_response(text: str) -> Verdict:
    obj = _first_json_object(text or "")
    if obj is None:
        return Verdict("invalid", error="no JSON object in reply")
    raw = str(obj.get("verdict", "")).strip().lower().replace("-", "_")
    verdict = _SYNONYMS.get(raw) or _SYNONYMS.get(raw.replace("_", " "))
    if verdict is None:
        return Verdict("invalid", rationale=str(obj.get("rationale", "")),
                       error=f"unknown verdict {obj.get('verdict')!r}")
    evidence = []
    for item in obj.get("evidence") or []:
        if isinstance(item, dict) and "id" in item:
            evidence.append({"id": str(item["id"]).strip("[] "), "value": str(item.get("value", ""))})
        elif isinstance(item, str):
            evidence.append({"id": item.strip("[] "), "value": ""})
    return Verdict(verdict, evidence, str(obj.get("rationale", "")))
