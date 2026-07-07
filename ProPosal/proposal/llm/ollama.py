"""Ollama backend — talks to a local daemon over stdlib urllib (no pip dep).

POSTs to ``{host}/api/chat`` with ``stream:false`` and, for JSON tasks,
``format:"json"`` so output is parseable. Low temperature for determinism.
"""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.request

from .base import LLMBackend, LLMError


class OllamaBackend(LLMBackend):
    def __init__(self, host: str = "http://localhost:11434",
                 model: str = "qwen2.5:14b-instruct",
                 num_ctx: int = 16384, timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.host + "/api/tags", timeout=3):
                return True
        except (urllib.error.URLError, OSError):
            return False

    def complete(self, prompt: str, *, system: str = "", json: bool = True) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "stream": False,
            "messages": messages,
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
        }
        if json:
            payload["format"] = "json"
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = _json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        return (body.get("message") or {}).get("content", "")
