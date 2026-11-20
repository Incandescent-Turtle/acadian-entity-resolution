"""Pluggable LLM backends: `complete(system, user) -> str`.

  fake           deterministic rule-based stand-in (tests; no network)
  ollama         a local model through Ollama's /api/chat (e.g. a 4-bit 7-8B model, fits 8 GB)
  openai_compat  any OpenAI-compatible /chat/completions server: OpenRouter, or vLLM /
                 llama.cpp / TGI on a cluster. Key read from the env var `api_key_env`.

All real backends send temperature (default 0) and a seed when the server
accepts one, for reproducibility.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol

import httpx

from ..config import BackendConfig

_FACT_LINE = re.compile(r"^\[(?P<id>[AB](?:\.[a-z_0-9]+)+)\] (?P<value>.*)$", re.MULTILINE)


class LLMBackend(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class FakeBackend:
    """Reads the facts back out of the prompt and applies simple rules:
    same name + an agreeing date -> match; a birth year more than 5 years apart
    -> not_match; otherwise insufficient. Cites the facts it used.

    `hallucinate=True` also cites one fact that does not exist (for testing the
    faithfulness check)."""

    name = "fake"

    def __init__(self, hallucinate: bool = False):
        self.hallucinate = hallucinate

    def complete(self, system: str, user: str) -> str:
        facts = {m["id"]: m["value"] for m in _FACT_LINE.finditer(user)}

        def year(v: str | None) -> int | None:
            ys = re.findall(r"\d{4}", v or "")
            return int(ys[-1]) if ys else None

        evidence, verdict = [], "insufficient"
        name_a, name_b = facts.get("A.name", ""), facts.get("B.name", "")
        ya, yb = year(facts.get("A.birth.date")), year(facts.get("B.birth.date"))
        if ya and yb and abs(ya - yb) > 5:
            verdict = "not_match"
            evidence = ["A.birth.date", "B.birth.date"]
        elif name_a.lower().split()[-1:] == name_b.lower().split()[-1:] and name_a:
            agreeing = [s for s in ("birth.date", "death.date", "marriage1.date",
                                    "father.name", "mother.name")
                        if f"A.{s}" in facts and f"B.{s}" in facts
                        and (year(facts[f"A.{s}"]) == year(facts[f"B.{s}"]) if s.endswith("date")
                             else facts[f"A.{s}"].lower() == facts[f"B.{s}"].lower())]
            if agreeing:
                verdict = "match"
                evidence = ["A.name", "B.name"] + [f"{x}.{s}" for s in agreeing for x in "AB"]
        cited = [{"id": i, "value": facts[i]} for i in evidence[:8]]
        if self.hallucinate:
            cited.append({"id": "A.godparent.name", "value": "Jean Untel"})
        return json.dumps({"verdict": verdict, "evidence": cited,
                           "rationale": "rule-based fake backend"})


class OllamaBackend:
    name = "ollama"

    def __init__(self, cfg: BackendConfig):
        self.cfg = cfg
        self.url = (cfg.base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")

    def complete(self, system: str, user: str) -> str:
        options = {"temperature": self.cfg.temperature}
        if self.cfg.seed is not None:
            options["seed"] = self.cfg.seed
        body = {"model": self.cfg.model, "stream": False, "options": options,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if self.cfg.json_mode:
            body["format"] = "json"
        r = httpx.post(f"{self.url}/api/chat", json=body, timeout=self.cfg.timeout_s)
        r.raise_for_status()
        return r.json()["message"]["content"]


class OpenAICompatBackend:
    name = "openai_compat"

    def __init__(self, cfg: BackendConfig):
        if not cfg.base_url:
            raise ValueError("openai_compat backend needs rq2.backend.base_url")
        self.cfg = cfg
        self.url = cfg.base_url.rstrip("/")
        self.key = os.environ.get(cfg.api_key_env, "") if cfg.api_key_env else ""

    def complete(self, system: str, user: str) -> str:
        body = {"model": self.cfg.model, "temperature": self.cfg.temperature,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if self.cfg.seed is not None:
            body["seed"] = self.cfg.seed
        if self.cfg.json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        r = httpx.post(f"{self.url}/chat/completions", json=body, headers=headers,
                       timeout=self.cfg.timeout_s)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def make_backend(cfg: BackendConfig) -> LLMBackend:
    if cfg.kind == "fake":
        return FakeBackend()
    if cfg.kind == "ollama":
        return OllamaBackend(cfg)
    if cfg.kind == "openai_compat":
        return OpenAICompatBackend(cfg)
    raise ValueError(f"unknown rq2.backend.kind {cfg.kind!r} (fake | ollama | openai_compat)")
