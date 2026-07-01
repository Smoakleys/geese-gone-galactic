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

from dataclasses import asdict
from typing import Callable

from control.store import RunRecord, RunStore, ControlMode
from harness.audit.cold_audit import AuditReport, cold_audit
from harness.checks.registry import Registry
from harness.gatekeeper import Gatekeeper
from harness.icarus.builder import Builder
from harness.loop import Loop
from harness.models import Ticket
from harness.review.base import Reviewer
from harness.review.decision_log_review import (
    DecisionLogReview,
    ProposedAdjustment,
    load_defect_records,
)
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
        stage_c_threshold: int = 3,
        audit_every: int = 0,
        auditor: Optional[Callable[[], AuditReport]] = None,
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
        self.stage_c_threshold = stage_c_threshold
        self.audit_every = audit_every
        self._auditor = auditor
        self._queue: list[Ticket] = []
        self._processed_tickets: dict[str, Ticket] = {}
        self._committed_since_audit = 0

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
            try:
                rec = self._run_one(ticket)
            except Exception as e:
                # Orchestration-level fail-closed: the loop already degrades builder/check/reviewer
                # errors to rejections (harness-mod-8/9/10), but a catastrophic per-ticket failure
                # (e.g. an unexpected commit/git error) must not kill the whole queue. Block this
                # ticket and move on — "run unattended, never require a human" holds end to end.
                rec = RunRecord(ticket_id=ticket.id, final_state="ERRORED", committed=False,
                                rounds=0, escape_hatch=False,
                                reason=f"runner caught {type(e).__name__}: {e}")
            self.store.record(rec)
            processed.append(rec)
            self._processed_tickets[ticket.id] = ticket

            # Periodic cold audit: acceptance is not forever. Every ``audit_every`` committed
            # tickets, re-verify the committed tree; a finding hard-blocks — STOP the runner so
            # no further work is accepted on top of a tree that no longer verifies.
            if self.audit_every and rec.committed:
                self._committed_since_audit += 1
                if self._committed_since_audit >= self.audit_every:
                    self._committed_since_audit = 0
                    report = self._run_audit()
                    self.store.record_audit(report.blocked, report.summary())
                    if report.blocked:
                        self.store.stop()
                        break
        # Stage C runs off the critical path, after the tickets are done: mine the builder
        # decision logs left in staging for subjective defects that recur often enough to be
        # worth turning into a deterministic Stage-A check. It never blocks or gates a commit.
        self.harvest_stage_c()
        return processed

    def _run_audit(self) -> AuditReport:
        """Run a cold audit over what's been accepted so far (injected auditor wins, for tests)."""
        if self._auditor is not None:
            return self._auditor()
        return cold_audit(self.gatekeeper, self.registry, reviewer=self.reviewer,
                          ticket_provider=self._processed_tickets.get)

    def harvest_stage_c(self) -> list[ProposedAdjustment]:
        """Harvest builder decision logs from the staging trees and surface check proposals.

        The decision logs live under ``staging_root/<ticket_id>/decision_log.jsonl`` and are in
        ``FORBIDDEN_ARTIFACT_NAMES`` — so they never entered ``game/accepted`` and Stage B never
        saw them. Here, post-acceptance, we read the reviewer defects the builder recorded,
        cluster the recurring ones, and persist any ``ProposedAdjustment``s to the store so the
        dashboard/summary can show them. This does not author checks (a guarded self-mod); it
        only proposes.
        """
        # Scope harvest to the tickets processed in THIS run, not every dir under staging_root.
        # In a persistent --workdir, staging dirs from earlier runs linger; globbing them would
        # re-harvest stale decision logs and inflate proposal counts across unrelated runs.
        records = []
        for tid in self._processed_tickets:
            log = self.staging_root / tid / "decision_log.jsonl"
            records.extend(load_defect_records(log, tid))
        # Pass the certified check ids so Stage C can tell "no gate exists yet" (propose a new
        # check) apart from "the gate exists but is too lax" (propose tightening it).
        existing = [c.id for c in self.registry.certified_checks()]
        proposals = DecisionLogReview(threshold=self.stage_c_threshold).analyze(records, existing)
        self.store.record_proposals([asdict(p) for p in proposals])
        # Mirror the monotonic ratchet floors so the read-only dashboard can show the
        # quality-never-regresses record without importing the gatekeeper.
        self.store.record_floors(self.gatekeeper.ratchet.floors())
        return proposals

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
