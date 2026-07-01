"""The strict iteration loop.

The loop advances the state machine and dispatches to the Builder and Reviewers. It holds
**no commit authority** — the ``COMMIT_PENDING -> RATCHET -> DONE`` edge belongs to the
Gatekeeper, which the loop *calls*, never bypasses. Every state change goes through
``states.assert_transition`` so an illegal shortcut is a crash, not a silent accept.

One ticket in, one ``IterationResult`` out. Rework loops feed the prior verdict's defects
back to the builder; ``max_rounds`` diverts to ``PLATEAU_ESCALATE`` instead of spinning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.checks.registry import Registry, stage_a_passed
from harness.gatekeeper import GateAborted, Gatekeeper
from harness.icarus.builder import Builder
from harness.metrics.plateau import PlateauDetector, defect_signature
from harness.models import (
    BuildPacket,
    CheckResult,
    Defect,
    Stage,
    Ticket,
    Verdict,
)
from harness.review.base import Reviewer
from harness.review.packet_builder import build_review_packet
from harness.states import State, assert_transition


@dataclass
class IterationResult:
    ticket_id: str
    final_state: State
    rounds: int
    committed: bool
    reason: str = ""
    git_sha: Optional[str] = None
    history: list[State] = field(default_factory=list)


class Loop:
    def __init__(
        self,
        *,
        repo_root: Path,
        builder: Builder,
        reviewer: Reviewer,
        registry: Registry,
        gatekeeper: Gatekeeper,
        staging_root: Optional[Path] = None,
        max_rounds: int = 3,
        plateau_window: int = 3,
    ):
        self.repo_root = Path(repo_root)
        self.builder = builder
        self.reviewer = reviewer
        self.registry = registry
        self.gatekeeper = gatekeeper
        self.staging_root = Path(staging_root or (self.repo_root / "run" / "staging"))
        self.max_rounds = max_rounds
        self.plateau_window = plateau_window

    def run_ticket(self, ticket: Ticket) -> IterationResult:
        history: list[State] = []

        def go(src: State, dst: State) -> State:
            assert_transition(src, dst)
            history.append(dst)
            return dst

        # TICKET_DRAFT -> TICKET_FROZEN (freeze here if the caller hasn't)
        state = State.TICKET_DRAFT
        history.append(state)
        if not ticket.frozen:
            ticket.freeze()
        state = go(state, State.TICKET_FROZEN)

        defects: list[Defect] = []
        rounds = 0
        plateau = PlateauDetector(window=self.plateau_window)

        def rework(src: State, signature: str, stage_label: str) -> Optional[IterationResult]:
            """Record the round's failure signature and decide: iterate, or escalate.

            Escalation fires on a *plateau* (same defect signature for `plateau_window`
            rounds — the loop is stuck) or on the hard `max_rounds` ceiling. Either way it
            hands off to the escape hatch instead of spinning forever."""
            plateau.record(signature=signature)
            st = go(src, State.REWORK)
            if plateau.plateaued():
                go(st, State.PLATEAU_ESCALATE)
                return IterationResult(ticket.id, State.PLATEAU_ESCALATE, rounds, False,
                                       f"plateau: stuck on {stage_label} '{signature}'",
                                       history=history)
            if rounds >= self.max_rounds:
                go(st, State.PLATEAU_ESCALATE)
                return IterationResult(ticket.id, State.PLATEAU_ESCALATE, rounds, False,
                                       f"plateau: max rounds ({self.max_rounds}) on {stage_label}",
                                       history=history)
            return None

        try:
            while True:
                rounds += 1
                staging_dir = self.staging_root / ticket.id
                _reset_dir(staging_dir)

                state = go(state, State.BUILDING)
                packet = BuildPacket(
                    ticket=ticket,
                    writable_root=str(staging_dir),
                    references=list(ticket.references),
                    defects=defects,
                )
                self.builder.build(packet)  # status is a claim; we ignore it

                # Tamper tripwire: a builder that mutated the frozen criteria mid-iteration
                # (goalpost-moving) is caught here before any review can be argued against a
                # relaxed spec. The Gatekeeper re-checks this independently.
                if ticket.is_tampered():
                    state = go(state, State.ABORTED_TAMPER)
                    return IterationResult(ticket.id, state, rounds, False,
                                           "ticket criteria changed after freeze", history=history)

                # --- Stage A -------------------------------------------------------
                state = go(state, State.STAGE_A_RUNNING)
                a_results: list[CheckResult] = self.registry.run_stage_a(staging_dir, ticket)
                if not stage_a_passed(a_results):
                    defects = _defects_from_stage_a(a_results)
                    escalated = rework(state, "A:" + (defect_signature(defects) or "reject"),
                                       "stage A")
                    if escalated is not None:
                        return escalated
                    state = State.REWORK
                    continue
                state = go(state, State.STAGE_A_PASS)

                # --- Stage B (isolated, fresh reviewer each round) -----------------
                state = go(state, State.STAGE_B_RUNNING)
                packet_b = build_review_packet(ticket=ticket, artifact_dir=staging_dir)
                verdict_b: Verdict = self.reviewer.review(packet_b, ticket)
                if not verdict_b.passed:
                    defects = list(verdict_b.defects)
                    escalated = rework(state, "B:" + (defect_signature(defects) or "reject"),
                                       "stage B")
                    if escalated is not None:
                        return escalated
                    state = State.REWORK
                    continue
                state = go(state, State.STAGE_B_PASS)

                # --- commit is the Gatekeeper's alone ------------------------------
                state = go(state, State.COMMIT_PENDING)
                outcome = self.gatekeeper.try_commit(
                    ticket=ticket,
                    staging_dir=staging_dir,
                    registry=self.registry,
                    stage_a_results=a_results,
                    verdict_b=verdict_b,
                )
                if not outcome.committed:
                    # Gatekeeper declined (should be rare here — both stages passed). Treat
                    # as rework rather than forcing an illegal COMMIT_PENDING->REWORK edge.
                    return IterationResult(ticket.id, State.REWORK, rounds, False,
                                           outcome.reason, history=history)
                state = go(state, State.RATCHET)
                state = go(state, State.DONE)
                return IterationResult(ticket.id, state, rounds, True, outcome.reason,
                                       git_sha=outcome.git_sha, history=history)
        except GateAborted as e:
            history.append(e.state)
            return IterationResult(ticket.id, e.state, rounds, False, e.reason, history=history)


def _reset_dir(d: Path) -> None:
    import shutil
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)


def _defects_from_stage_a(results: list[CheckResult]) -> list[Defect]:
    from harness.models import Result
    return [
        Defect(criterion=r.check_id, severity="blocking", detail=r.evidence, repro=f"check:{r.check_id}")
        for r in results if r.result == Result.FAIL
    ]
