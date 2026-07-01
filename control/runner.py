"""The autonomous runner — the thing that "keeps running" without a human.

It pulls tickets off a queue and drives each through the strict ``Loop``. The design goals map
directly to the standing order (intervene-optional, never-required):

* **Never blocks on a human.** When a ticket plateaus, the runner auto-escalates to the
  escape-hatch builder (a stronger/other builder) for one more attempt. If that also fails the
  ticket is marked ``blocked`` and the runner *moves on to the next ticket* — it never stops to
  ask. A human can look at ``blocked`` later, but nothing waits on them.
* **Intervention is one lever.** Between tickets the runner reads ``store.mode``; PAUSED or
  STOPPED makes it return cleanly (resumable). Start/Stop/Pause therefore work without any
  cooperation from the loop internals.
* **Heartbeat + telemetry.** Each ticket beats the heartbeat and records a ``RunRecord`` so the
  dashboard/phone can see liveness and the autonomy rate without touching the harness.

The runner has no commit authority of its own — it only calls ``Loop``, which calls the
Gatekeeper. Escalation is a builder swap, not a gate bypass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from control.store import RunRecord, RunStore, ControlMode
from harness.checks.registry import Registry
from harness.gatekeeper import Gatekeeper
from harness.icarus.builder import Builder
from harness.loop import Loop
from harness.models import Ticket
from harness.review.base import Reviewer
from harness.states import State


class AutonomousRunner:
    def __init__(
        self,
        *,
        store: RunStore,
        repo_root: Path,
        registry: Registry,
        gatekeeper: Gatekeeper,
        reviewer: Reviewer,
        icarus_builder: Builder,
        escape_hatch_builder: Optional[Builder] = None,
        staging_root: Optional[Path] = None,
        max_rounds: int = 3,
        plateau_window: int = 3,
    ):
        self.store = store
        self.repo_root = Path(repo_root)
        self.registry = registry
        self.gatekeeper = gatekeeper
        self.reviewer = reviewer
        self.icarus_builder = icarus_builder
        self.escape_hatch_builder = escape_hatch_builder
        self.staging_root = Path(staging_root or (self.repo_root / "run" / "staging"))
        self.max_rounds = max_rounds
        self.plateau_window = plateau_window
        self._queue: list[Ticket] = []

    def submit(self, ticket: Ticket) -> None:
        self._queue.append(ticket)

    @property
    def pending(self) -> int:
        return len(self._queue)

    def _loop_with(self, builder: Builder) -> Loop:
        return Loop(
            repo_root=self.repo_root, builder=builder, reviewer=self.reviewer,
            registry=self.registry, gatekeeper=self.gatekeeper,
            staging_root=self.staging_root, max_rounds=self.max_rounds,
            plateau_window=self.plateau_window,
        )

    def run_pending(self, max_tickets: Optional[int] = None) -> list[RunRecord]:
        """Process queued tickets until empty, paused/stopped, or ``max_tickets`` reached."""
        processed: list[RunRecord] = []
        while self._queue:
            if self.store.mode is not ControlMode.RUNNING:
                break  # paused/stopped: return cleanly, queue intact, fully resumable
            if max_tickets is not None and len(processed) >= max_tickets:
                break
            ticket = self._queue.pop(0)
            self.store.beat()
            rec = self._run_one(ticket)
            self.store.record(rec)
            processed.append(rec)
        return processed

    def _run_one(self, ticket: Ticket) -> RunRecord:
        result = self._loop_with(self.icarus_builder).run_ticket(ticket)
        escape = False

        if (result.final_state == State.PLATEAU_ESCALATE
                and self.escape_hatch_builder is not None):
            # Auto-escalation: hand the same frozen ticket to the escape-hatch builder for one
            # more attempt. No human is consulted; this is the whole point of the escape hatch.
            escape = True
            result = self._loop_with(self.escape_hatch_builder).run_ticket(ticket)

        return RunRecord(
            ticket_id=ticket.id,
            final_state=result.final_state.value,
            committed=result.committed,
            rounds=result.rounds,
            escape_hatch=escape,
            reason=result.reason,
        )
