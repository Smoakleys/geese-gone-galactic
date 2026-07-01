"""Icarus as a real builder behind a swappable generation seam.

``StubBuilder`` proved the loop; ``LLMBuilder`` is the shape Icarus actually takes: it asks a
``GenerationClient`` for artifact contents, writes them into the gitignored staging root, and
records a decision log. The client is the swap point — scripted in tests, a local model or a
paid API in production — so the builder code, the loop, and the gate never change when the
brain behind Icarus is upgraded.

Two properties are preserved by construction, not by prompt discipline:

* **No commit path.** The builder writes only under ``packet.writable_root`` and returns a
  ``BuildResult`` whose ``status`` is a claim the Gatekeeper is free to ignore.
* **Feeds the flywheel.** Every defect the builder was handed for rework is written to the
  decision log as a ``{"defect": {...}}`` line, so Stage C can later harvest recurring
  subjective defects into new deterministic checks. The decision log stays builder-private —
  Stage B never sees it.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from harness.icarus.builder import Builder
from harness.models import BuildPacket, BuildResult, BuildStatus


@runtime_checkable
class GenerationClient(Protocol):
    """Produces artifact files for a ticket. Returns ``{relative_path: text_contents}``."""

    model_id: str

    def generate(self, packet: BuildPacket) -> dict[str, str]: ...


class ScriptedGenerationClient(GenerationClient):
    """Deterministic offline generator. ``script(packet) -> {relpath: contents}``."""

    def __init__(self, script: Callable[[BuildPacket], dict[str, str]], model_id: str = "scripted-icarus"):
        self._script = script
        self.model_id = model_id

    def generate(self, packet: BuildPacket) -> dict[str, str]:
        return dict(self._script(packet))


class LLMBuilder(Builder):
    """Icarus. Delegates content creation to a ``GenerationClient`` and handles all I/O."""

    def __init__(self, client: GenerationClient):
        self._client = client

    @property
    def id(self) -> str:
        return f"icarus:{self._client.model_id}"

    def build(self, packet: BuildPacket) -> BuildResult:
        root = Path(packet.writable_root)
        root.mkdir(parents=True, exist_ok=True)

        files = self._client.generate(packet)
        self._write_decision_log(root, packet, files)

        if not files:
            # An honest give-up is first-class: it triggers escape-hatch + an Icarus-upgrade
            # signal, never a silent empty commit (Stage A will also reject nothing).
            return BuildResult(BuildStatus.GAVE_UP, str(root),
                               str(root / "decision_log.jsonl"), notes="generator produced nothing")

        for rel, contents in files.items():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(contents)

        return BuildResult(BuildStatus.COMPLETED, str(root),
                           str(root / "decision_log.jsonl"),
                           notes=f"icarus wrote {len(files)} file(s)")

    def _write_decision_log(self, root: Path, packet: BuildPacket, files: dict[str, str]) -> None:
        log = root / "decision_log.jsonl"
        with log.open("w") as fh:
            fh.write(json.dumps({
                "step": "generate",
                "builder": self.id,
                "files": sorted(files.keys()),
                "rationale": f"generated artifacts for {packet.ticket.id}",
            }) + "\n")
            # Carry forward the defects we were told to fix, so Stage C can mine recurring ones.
            for d in packet.defects:
                fh.write(json.dumps({"defect": asdict(d)}) + "\n")
