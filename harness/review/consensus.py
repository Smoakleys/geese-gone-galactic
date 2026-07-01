"""Multi-model consensus review — fail-closed by construction.

A single reviewer model has a single blind spot; a wrong PASS from one model is exactly the
failure the visual gate has fallen for before. Consensus removes the single point of failure:
N independent models each answer every criterion, and a criterion counts as PASSed only if
**every** model attests it with evidence (unanimity). The moment models disagree, the
criterion FAILs and a ``model_disagreement`` defect is raised — a split vote is treated as a
finding to escalate, never averaged into a pass.

This is deliberately conservative: raising N can only make the gate stricter, never looser.
It cannot manufacture a PASS the individual models didn't all give.
"""

from __future__ import annotations

from harness.models import CriterionVerdict, Defect, Result, Stage, Ticket, Verdict
from harness.review.llm_reviewer import decompose_packet
from harness.review.model_client import ChatClient
from harness.review.packet_builder import ReviewPacket


class ConsensusReviewer:
    """Stage-B reviewer that requires unanimous PASS across several ``ChatClient`` models."""

    def __init__(self, clients: list[ChatClient], *, reviewer_prefix: str = "consensus"):
        if not clients:
            raise ValueError("consensus review needs at least one model client")
        self._clients = clients
        self._prefix = reviewer_prefix
        self._round = 0

    @property
    def id(self) -> str:
        return f"{self._prefix}({'+'.join(c.model_id for c in self._clients)})"

    def review(self, packet: ReviewPacket, ticket: Ticket) -> Verdict:
        rnd = self._round
        self._round += 1
        reviewer_id = f"{self.id}#r{rnd}"

        request = decompose_packet(packet)
        # One fresh call per model; no state shared between them.
        replies = {c.model_id: c.complete(request).by_id() for c in self._clients}

        per: list[CriterionVerdict] = []
        defects: list[Defect] = []
        for c in packet.criteria:
            votes = {mid: ans.get(c.id) for mid, ans in replies.items()}
            passes = {
                mid for mid, a in votes.items()
                if a is not None and a.passed and a.evidence.strip()
            }
            if len(passes) == len(self._clients):
                # unanimous, evidence-backed PASS
                evidence = "; ".join(
                    f"{mid}: {votes[mid].evidence}" for mid in sorted(passes)
                )
                per.append(CriterionVerdict(id=c.id, result=Result.PASS, evidence=evidence))
                continue

            per.append(CriterionVerdict(id=c.id, result=Result.FAIL, evidence=""))
            dissenters = sorted(set(replies) - passes)
            if passes and dissenters:
                detail = (f"model disagreement on {c.id}: PASS={sorted(passes)} "
                          f"FAIL/blank={dissenters}")
            else:
                detail = f"no model attested {c.id}"
            defects.append(Defect(criterion=c.id, severity="blocking", detail=detail,
                                  repro=f"consensus:{reviewer_id}"))

        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id=reviewer_id,
                             per_criterion=per, defects=defects)
