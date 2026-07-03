"""OllamaAgentModel — Icarus's local chat brain behind the AgentModel seam.

Talks to a local Ollama server (`POST /api/chat`). Model is a free variable (gpt-oss:20b is the
measured default on the 16GB RX 9070 XT); swap per ticket. Kept import-light (stdlib urllib) so
the runtime has no heavy deps; the network call is only exercised live, never in the offline suite.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class OllamaAgentModel:
    def __init__(self, model_id: str = "gpt-oss:20b",
                 endpoint: str = "http://localhost:11434",
                 timeout: float = 240.0, temperature: float = 0.3, num_ctx: int = 8192,
                 retries: int = 3, keep_alive: str = "30m",
                 num_predict: "int | None" = None) -> None:
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.retries = retries
        # keep_alive keeps the model resident between turns so it is not evicted + reloaded (a reload of
        # the offloaded 30B costs many seconds every turn). num_predict optionally caps generation.
        self.keep_alive = keep_alive
        self.num_predict = num_predict

    def complete(self, messages: list[dict[str, str]]) -> str:
        options = {"temperature": self.temperature, "num_ctx": self.num_ctx}
        if self.num_predict is not None:
            options["num_predict"] = self.num_predict
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": options,
        }
        data = json.dumps(payload).encode("utf-8")
        last_err: Exception | None = None
        # Ollama returns a transient HTTP 500 while a model reloads (eviction/keep-alive). Retry with
        # backoff so a blip never takes Icarus "down" — a real failure still raises after N tries.
        for attempt in range(max(1, self.retries)):
            try:
                req = urllib.request.Request(self.endpoint + "/api/chat", data=data,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read())
                msg = body.get("message", {})
                content = msg.get("content") or ""
                # Reasoning models (gpt-oss) sometimes leave content empty and put everything in the
                # 'thinking' channel; fall back to it so a tool block emitted there is still seen.
                if not content.strip():
                    content = msg.get("thinking") or ""
                return content
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
                if attempt < self.retries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Ollama /api/chat failed after {self.retries} tries: {last_err}")
