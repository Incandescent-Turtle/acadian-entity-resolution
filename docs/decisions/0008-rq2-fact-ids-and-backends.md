# 0008 — RQ2 evidence by fact ID; OpenAI-compatible backend

**Context.**
- RQ2 must check that the evidence an LLM cites is actually in its context. Free-text
  quotes are hard to verify.
- The user will run models through OpenRouter or on a cluster (a local model), and
  locally through Ollama.

**Decision.**
- **Fact IDs.** Every fact is rendered as `[ID] value`. IDs are role paths such as
  `A.birth.date`, `B.father.name` and `A.spouse1.mother.death.place`. The model must
  reply with JSON: verdict, evidence as `[{id, value}]`, and a rationale.
- **Faithfulness.** A citation is faithful if its ID exists and its value matches the
  fact after normalisation (containment either way, so "1745" matches
  "ABT 12 MAR 1745").
- **Parsing.** Tolerant: fences, surrounding text and verdict synonyms are accepted.
  Unparseable replies are `invalid`, never silently mapped to a verdict.
- **Backends.**
  - `fake`: deterministic and offline, cites only real facts, with an option to
    hallucinate one citation.
  - `ollama`: `/api/chat` with JSON format.
  - `openai_compat`: one backend for OpenRouter **and** vLLM / llama.cpp / TGI cluster
    servers, since they all speak `/chat/completions`. The key comes from an env var
    named in the config.
  - Temperature defaults to 0, and a seed is sent where supported.

**Consequences.**
- Faithfulness checks are exact and automatic.
- IDs are path-based, so k=0 and k=2 share the IDs of the two records.
- Some servers reject `response_format` or `seed`; set `json_mode: false` or
  `seed: null` in the config for those.
- No provider SDK dependency: `httpx` only.
