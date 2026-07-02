"""Icarus for real — the local model that actually builds, behind the ``GenerationClient`` seam.

This is the piece the whole project exists to bootstrap: a **local**, model-agnostic coding agent
(Ollama, default ``qwen3-coder:30b``) that takes a bounded ticket + acceptance criteria and emits
the artifact files. It slots in exactly where the scripted stub did — ``LLMBuilder`` handles all
I/O and the decision log; this only turns a ``BuildPacket`` into ``{relpath: contents}`` by asking
the local model. Claude authors the ticket and gates the result; Icarus does the building. As
Icarus earns trust the autonomy rate climbs — that is the north star.

Stdlib-only (urllib) so it stays importable anywhere the harness core does. The model is told to
emit files in a strict, un-prose fenced format so the output is deterministically parseable:

    ===FILE: relative/path.gd===
    <full file contents>
    ===END===
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Optional

from harness.models import BuildPacket

_FILE_RE = re.compile(r"===FILE:\s*(?P<path>.+?)\s*===\r?\n(?P<body>.*?)\r?\n===END===", re.DOTALL)

_SYSTEM = (
    "You are Icarus, a focused local coding agent building the game Geese Gone Galactic. "
    "Implement the ticket by emitting COMPLETE files and nothing else. Output every file as:\n"
    "===FILE: <relative/path>===\n<full file contents>\n===END===\n"
    "Emit no prose, explanations, or markdown fences — only ===FILE=== blocks. Satisfy every "
    "acceptance criterion. If given prior defects, fix them."
)


class OllamaGenerationClient:
    """A ``GenerationClient`` backed by a local Ollama model. Icarus's real brain."""

    def __init__(self, model_id: str = "qwen3-coder:30b",
                 endpoint: str = "http://localhost:11434", timeout: float = 600.0,
                 temperature: float = 0.2):
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature

    # -- the seam ----------------------------------------------------------------------

    def generate(self, packet: BuildPacket) -> dict[str, str]:
        """Ask the local model to implement the ticket; return ``{relpath: contents}``."""
        reply = self._chat(_SYSTEM, self._prompt(packet))
        return parse_files(reply)

    # -- prompt + transport ------------------------------------------------------------

    def _prompt(self, packet: BuildPacket) -> str:
        t = packet.ticket
        lines = [f"Ticket {t.id}: {t.title}", "", "Acceptance criteria (ALL must hold):"]
        for c in t.acceptance_criteria:
            hint = f"  [check: {c.check_hint}]" if getattr(c, "check_hint", None) else ""
            lines.append(f"- ({c.id}) {c.text}{hint}")
        if packet.references:
            lines += ["", "References: " + ", ".join(packet.references)]
        if packet.defects:
            lines += ["", "Fix these defects from the last attempt:"]
            for d in packet.defects:
                lines.append(f"- {d.criterion}: {d.detail}")
        lines += ["", "Emit the complete file(s) that satisfy the criteria, in ===FILE=== blocks."]
        return "\n".join(lines)

    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint + "/api/chat", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        return body.get("message", {}).get("content", "")


def parse_files(reply: str) -> dict[str, str]:
    """Extract ``{relpath: contents}`` from a model reply of ===FILE=== blocks.

    An empty dict (model emitted no parseable file) is an honest give-up — ``LLMBuilder`` turns
    that into a GAVE_UP result and Stage A rejects nothing, so a lazy/confused model never
    produces a silent empty commit.
    """
    files: dict[str, str] = {}
    for m in _FILE_RE.finditer(reply or ""):
        path = m.group("path").strip().strip("`").strip()
        if path:
            files[path] = m.group("body")
    return files


def ollama_available(endpoint: str = "http://localhost:11434", timeout: float = 3.0) -> Optional[list[str]]:
    """Return the list of local model names if Ollama is reachable, else None (never raises)."""
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/api/tags", timeout=timeout) as resp:
            tags = json.loads(resp.read()).get("models", [])
        return [t.get("name", "") for t in tags]
    except Exception:
        return None
