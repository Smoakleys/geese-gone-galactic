"""AgentBuilder — drive Icarus's agent runtime behind the harness Builder seam.

Wraps the plan->act->reflect loop so the gatekeeper-fronted loop can build real tickets with the
*agent* (tools, perception, memory), not a one-shot generator. Like every builder it writes ONLY
inside ``packet.writable_root`` (the gitignored staging dir) and has no commit path — the returned
``status`` is a claim the gate is free to ignore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from harness.icarus.agent import AgentModel, Notebook, VisionModel, run_agent
from harness.icarus.builder import Builder
from harness.models import BuildPacket, BuildResult, BuildStatus

_LOG_NAME = "decision_log.jsonl"


def task_from_packet(packet: BuildPacket) -> str:
    """Turn a ticket (+ any rework defects) into the natural-language task the agent solves."""
    t = packet.ticket
    lines = [t.title]
    crits = list(getattr(t, "acceptance_criteria", None) or [])
    if crits:
        lines.append("\nAcceptance criteria (your work must satisfy ALL of these):")
        lines += [f"- {getattr(c, 'text', str(c))}" for c in crits]
    if packet.references:
        lines.append("\nReference files you may read: " + ", ".join(packet.references))
    if packet.defects:
        lines.append("\nA previous attempt FAILED with these problems - fix them:")
        lines += [f"- {getattr(d, 'detail', str(d))}" for d in packet.defects]
    return "\n".join(lines)


class AgentBuilder(Builder):
    def __init__(self, model: AgentModel, *, vision: "Optional[VisionModel]" = None,
                 notebook: "Optional[Notebook]" = None, render_fn=None,
                 max_steps: int = 16, run_timeout: float = 90.0, use_notebook: bool = True) -> None:
        self._model = model
        self._vision = vision
        self._notebook = notebook
        self._render_fn = render_fn
        self._max_steps = max_steps
        self._run_timeout = run_timeout
        self._use_notebook = use_notebook

    @property
    def id(self) -> str:
        return f"icarus-agent:{getattr(self._model, 'model_id', 'scripted')}"

    def build(self, packet: BuildPacket) -> BuildResult:
        root = Path(packet.writable_root)
        root.mkdir(parents=True, exist_ok=True)
        result = run_agent(self._model, task_from_packet(packet), root,
                           max_steps=self._max_steps, run_timeout=self._run_timeout,
                           vision=self._vision, notebook=self._notebook,
                           use_notebook=self._use_notebook, render_fn=self._render_fn)

        log = root / _LOG_NAME
        self._write_decision_log(log, result)

        produced = [p for p in root.rglob("*") if p.is_file() and p.name != _LOG_NAME]
        note = f"agent {result.state.value} in {result.steps} step(s); {len(produced)} file(s)"
        if not produced:
            # Produced nothing usable -> GAVE_UP triggers the escape hatch + an Icarus-upgrade signal.
            return BuildResult(BuildStatus.GAVE_UP, str(root), str(log), notes=note)
        return BuildResult(BuildStatus.COMPLETED, str(root), str(log), notes=note)

    @staticmethod
    def _write_decision_log(log: Path, result) -> None:
        # The decision log must reach Stage C (harvesting) but never Stage B (reviewer isolation).
        with log.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"step": "plan", "choice": (result.plan or "")[:400],
                                 "rationale": "the agent's stated approach",
                                 "alternatives_considered": []}) + "\n")
            fh.write(json.dumps({"step": "outcome", "choice": result.state.value,
                                 "rationale": f"finished={result.finished}, steps={result.steps}",
                                 "alternatives_considered": []}) + "\n")
