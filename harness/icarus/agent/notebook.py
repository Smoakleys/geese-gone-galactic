"""Icarus's durable notebook — cross-task memory (lessons, gotchas, strategies).

The agent reads it at the start of a task and appends to it with the `note` tool, so it stops
re-learning the same things. Guarded by the strip-to-test discipline: ``run_agent(use_notebook=False)``
disables injection, so we can measure whether a skill actually *stuck* (unaided) vs. is a crutch —
the dependence-gap metric. Plain markdown so it's human-reviewable and prunable (Hermes-style
curation/compaction is a future step, to keep it high-signal rather than append-noise).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path


class Notebook:
    def __init__(self, path) -> None:
        self.path = Path(path)

    def read(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8", errors="replace")

    def entries(self) -> list[str]:
        return [ln for ln in self.read().splitlines() if ln.strip()]

    def append(self, entry: str) -> bool:
        """Append one lesson. Returns False for empty or exact-duplicate entries (cheap de-dup)."""
        entry = " ".join(entry.split()).strip()
        if not entry:
            return False
        if any(entry in ln for ln in self.entries()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(f"- [{date.today().isoformat()}] {entry}\n")
        return True
