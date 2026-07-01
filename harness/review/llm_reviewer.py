"""A real Stage-B reviewer that sits behind the ``ChatClient`` seam.

This is the Phase-2 replacement for ``StubReviewer``: it decomposes the isolated
``ReviewPacket`` into one question per Stage-B criterion, asks a model (any ``ChatClient`` —
scripted in tests, Anthropic in production, or several via the consensus wrapper), and folds
the answers back into a ``Verdict``. It adds **no** authority of its own: the overall verdict
stays derived/default-FAIL, and every model answer without concrete evidence collapses to
FAIL. A fresh ``reviewer_id`` is minted per call to model the "new session per round" rule.

Because it only ever reads the packet the isolation builder produced, the reviewer cannot see
the decision log, prior verdicts, or loop memory — the same construction guarantee that makes
Stage B adversarial rather than a review of the builder's own justifications.
"""

from __future__ import annotations

from harness.models import CriterionVerdict, Defect, Result, Stage, Ticket, Verdict
from harness.review.model_client import (
    ChatClient,
    CriterionQuestion,
    ModelRequest,
)
from harness.review.packet_builder import ReviewPacket

_SYSTEM = (
    "You are a fresh, zero-context adversarial reviewer for a game-asset build. You have never "
    "seen this ticket before and you cannot see the builder's reasoning. Judge only the artifact "
    "against each acceptance criterion. Default to FAIL unless the evidence is concrete."
)


class LLMReviewer:
    """Stage-B reviewer over a single ``ChatClient``. Swap the client to swap the model."""

    def __init__(self, client: ChatClient, *, reviewer_prefix: str = "llm"):
        self._client = client
        self._prefix = reviewer_prefix
        self._round = 0

    @property
    def id(self) -> str:
        return f"{self._prefix}:{self._client.model_id}"

    def review(self, packet: ReviewPacket, ticket: Ticket) -> Verdict:
        rnd = self._round
        self._round += 1
        reviewer_id = f"{self.id}#r{rnd}"  # fresh identity per round; no carryover

        request = decompose_packet(packet)
        reply = self._client.complete(request)
        answers = reply.by_id()

        per: list[CriterionVerdict] = []
        defects: list[Defect] = []
        for c in packet.criteria:
            ans = answers.get(c.id)
            if ans is not None and ans.passed and ans.evidence.strip():
                per.append(CriterionVerdict(id=c.id, result=Result.PASS, evidence=ans.evidence))
            else:
                evidence = ans.evidence if ans else ""
                per.append(CriterionVerdict(id=c.id, result=Result.FAIL, evidence=""))
                defects.append(Defect(
                    criterion=c.id, severity="blocking",
                    detail=evidence or f"{reviewer_id} did not attest {c.id}",
                    repro=f"review:{reviewer_id}",
                ))

        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id=reviewer_id,
                             per_criterion=per, defects=defects)


def decompose_packet(packet: ReviewPacket) -> ModelRequest:
    """Decompose an isolated review packet into one question per Stage-B criterion.

    Reference-anchored review is per-criterion, never a single "does this look good?" — the
    model answers each criterion independently so one weak answer can't be hidden inside a
    global thumbs-up. Shared by the single-model and consensus reviewers so both send an
    identical, isolation-preserving request.
    """
    questions = [
        CriterionQuestion(id=c.id, text=c.text, rubric_ref=c.rubric_ref)
        for c in packet.criteria
    ]
    # Only textual artifacts go in the text channel; image paths are carried separately by the
    # visual gate. Binary placeholders are dropped rather than shipped as noise.
    artifact_text = {
        name: body for name, body in packet.artifact_files.items()
        if not body.startswith("<binary ")
    }
    image_paths = [
        name for name, body in packet.artifact_files.items() if body.startswith("<binary ")
    ]
    return ModelRequest(
        ticket_id=packet.ticket_id,
        criteria_hash=packet.criteria_hash,
        system=_SYSTEM,
        questions=questions,
        artifact_text=artifact_text,
        image_paths=image_paths,
        reference_paths=list(packet.reference_paths),
    )
