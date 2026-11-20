"""RQ2: LLM verification of a candidate pair (match / not_match / insufficient),
with cited evidence, for k=0 (two records) vs k=2 (records + 2-hop family)."""

from .backends import FakeBackend, LLMBackend, OllamaBackend, OpenAICompatBackend, make_backend
from .context import Fact, PairContext, build_context
from .faithfulness import check_faithfulness
from .labels import LabelledPair, read_labels, write_labels
from .metrics import verification_metrics
from .parse import Verdict, parse_response
from .prompt import build_prompt

__all__ = ["FakeBackend", "LLMBackend", "OllamaBackend", "OpenAICompatBackend", "make_backend",
           "Fact", "PairContext", "build_context", "check_faithfulness", "LabelledPair",
           "read_labels", "write_labels", "verification_metrics", "Verdict", "parse_response",
           "build_prompt"]
