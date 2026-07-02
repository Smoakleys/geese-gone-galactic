"""OllamaVisionModel — Icarus's eyes.

Describes an image via a local vision model (qwen2.5vl:7b by default) over Ollama's `/api/chat`
(images passed as base64). This is what lets the agent *look* at a render/screenshot and reason
about it, instead of building blind. Stdlib-only transport; only exercised live, never offline.
"""

from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path


class OllamaVisionModel:
    def __init__(self, model_id: str = "qwen2.5vl:7b",
                 endpoint: str = "http://localhost:11434", timeout: float = 300.0) -> None:
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def describe(self, image_path: str,
                 question: str = "Describe this image in detail. What objects and layout do you see?") -> str:
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        payload = {
            "model": self.model_id,
            "stream": False,
            "messages": [{"role": "user", "content": question, "images": [b64]}],
        }
        req = urllib.request.Request(self.endpoint + "/api/chat", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        return body.get("message", {}).get("content", "")
