"""OllamaAgentModel — Icarus's local chat brain behind the AgentModel seam.

Talks to a local Ollama server (`POST /api/chat`). Model is a free variable (gpt-oss:20b is the
measured default on the 16GB RX 9070 XT); swap per ticket. Kept import-light (stdlib urllib) so
the runtime has no heavy deps; the network call is only exercised live, never in the offline suite.
"""

from __future__ import annotations

import json
import urllib.request


class OllamaAgentModel:
    def __init__(self, model_id: str = "gpt-oss:20b",
                 endpoint: str = "http://localhost:11434",
                 timeout: float = 600.0, temperature: float = 0.3, num_ctx: int = 8192) -> None:
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.num_ctx = num_ctx

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint + "/api/chat", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        msg = body.get("message", {})
        content = msg.get("content") or ""
        # Reasoning models (e.g. gpt-oss) sometimes leave content empty and put everything in the
        # 'thinking' channel; fall back to it so a tool block emitted there is still seen.
        if not content.strip():
            content = msg.get("thinking") or ""
        return content
