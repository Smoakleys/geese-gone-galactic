"""Icarus's durable Godot notebook — a committed, growing set of general Godot lessons.

`godot_notebook()` returns a Notebook backed by the committed `godot_lessons.md`, so Godot tickets
start with the distilled gotchas (look_at ordering, camera framing, unshaded materials, ...) that
turn a valid-but-empty render into a visible scene. General domain knowledge, curated by Claude and
extendable by Icarus (subject to the strip-to-test discipline).
"""

from __future__ import annotations

from pathlib import Path

from harness.icarus.agent import Notebook

LESSONS_PATH = Path(__file__).parent / "godot_lessons.md"


def godot_notebook() -> Notebook:
    """Read-only access to the CURATED seed (for injecting the lessons into a run)."""
    return Notebook(LESSONS_PATH)


def godot_working_notebook(work_dir) -> Notebook:
    """A per-run WORKING COPY of the curated seed. Icarus may append `note`s here freely without
    polluting the committed seed (a struggling model otherwise fills it with confused scratch notes -
    observed live). Promoting a good working-copy lesson back into the seed is a deliberate curation
    step, never an auto-append."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    dst = work_dir / "godot_notebook.md"
    dst.write_text(LESSONS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return Notebook(dst)
