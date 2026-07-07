"""Pluggable local-LLM backends for ProPosal.

Per docs/phase6-requirements-llm.md: start on a local Ollama daemon (nothing leaves
the machine — these are confidential submittals), designed so a Claude API backend
could slot in later without rearchitecting. First consumer is the Section I skill
classifier (``proposal.skills``); the planned requirements checker will reuse it.

Nothing here adds a hard dependency: the Ollama backend talks to the daemon over
stdlib ``urllib``, and callers treat a ``None`` backend (disabled or unreachable) as
"fall back to deterministic behaviour".
"""

from __future__ import annotations

from .base import LLMBackend, LLMError
from .ollama import OllamaBackend

__all__ = ["LLMBackend", "LLMError", "OllamaBackend", "get_backend"]


def get_backend(cfg: dict | None) -> LLMBackend | None:
    """Build the configured backend, or ``None`` if LLM use is disabled.

    Returns ``None`` when ``cfg['llm']['enabled']`` is falsy so callers can cheaply
    branch to their deterministic path.
    """
    llm = (cfg or {}).get("llm") or {}
    if not llm.get("enabled"):
        return None
    backend = (llm.get("backend") or "ollama").lower()
    if backend == "ollama":
        return OllamaBackend(
            host=llm.get("host", "http://localhost:11434"),
            model=llm.get("model", "qwen2.5:14b-instruct"),
            num_ctx=int(llm.get("num_ctx", 16384) or 16384),
        )
    raise LLMError(f"Unknown LLM backend: {backend!r}")
