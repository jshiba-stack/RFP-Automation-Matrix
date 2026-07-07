"""LLM backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when a backend cannot produce a completion."""


class LLMBackend(ABC):
    """Minimal text-completion interface a backend must provide."""

    @abstractmethod
    def complete(self, prompt: str, *, system: str = "", json: bool = True) -> str:
        """Return the model's text for ``prompt``.

        When ``json`` is true the backend should constrain output to valid JSON
        (the caller still validates/repairs). Raises ``LLMError`` on failure.
        """

    def available(self) -> bool:
        """Best-effort reachability check; backends override. Default: assume yes."""
        return True
