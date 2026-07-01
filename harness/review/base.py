"""Reviewer contract + a scripted stub reviewer for the walking skeleton.

A real Stage-B reviewer (Phase 2) is a fresh zero-context Opus session that receives only a
``ReviewPacket`` and returns per-criterion PASS/FAIL with evidence. The stub here returns a
scripted sequence so tests can drive FAIL-then-PASS deterministically. Either way the
reviewer's output is a ``Verdict`` whose overall value is *derived* (default-FAIL), never
asserted by the reviewer directly.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from harness.models import CriterionVerdict, Result, Stage, Ticket, Verdict
from harness.review.packet_builder import ReviewPacket


@runtime_checkable
class Reviewer(Protocol):
    id: str

    def review(self, packet: ReviewPacket, ticket: Ticket) -> Verdict: ...


class StubReviewer(Reviewer):
    """Scripted reviewer. ``script(round) -> bool`` decides pass/fail for the whole packet.

    On PASS it attaches non-empty evidence to every Stage-B criterion (so the default-FAIL
    coercion is satisfied); on FAIL it emits a blocking defect. A fresh ``reviewer_id`` is
    minted per call to model the "new session per review" property.
    """

    id = "stub-reviewer"

    def __init__(self, script: Callable[[int], bool]):
        self._script = script
        self._round = 0

    def review(self, packet: ReviewPacket, ticket: Ticket) -> Verdict:
        rnd = self._round
        self._round += 1
        reviewer_id = f"stub-reviewer-r{rnd}"  # fresh id per round; no carryover

        will_pass = self._script(rnd)
        if will_pass:
            per = [
                CriterionVerdict(id=c.id, result=Result.PASS, evidence=f"criterion {c.id} met (stub)")
                for c in packet.criteria
            ]
            return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id=reviewer_id, per_criterion=per)

        from harness.models import Defect
        per = [CriterionVerdict(id=c.id, result=Result.FAIL, evidence="") for c in packet.criteria]
        defects = [Defect(criterion=(packet.criteria[0].id if packet.criteria else "-"),
                           severity="blocking", detail="stub reviewer rejected", repro="n/a")]
        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id=reviewer_id,
                             per_criterion=per, defects=defects)
