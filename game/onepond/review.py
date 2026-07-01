"""The One Pond Stage-B reviewer: a *seeing* CV floor beneath the subjective reviewer.

`ReferenceAnchoredScorer` and `StubScreenshotWorker` existed and were tested, but nothing in a
live run actually rendered the config and looked at it — Stage B was the scripted/LLM reviewer
alone. This wires the visual gate into the pipeline behind the existing ``Reviewer`` seam, so
every One Pond acceptance is visually gated end to end.

Composition mirrors the visual-gate design note: the CV layer is the *mechanical floor* of
Stage B, and the model/scripted reviewer supplies the subjective judgement above it. Both must
pass. So this reviewer renders the config, runs the scorer, and:

* if the render can't be scored as a real pond -> a blocking visual defect (the subjective
  reviewer is never even consulted — no point arguing taste about a blank frame);
* otherwise it delegates to the wrapped base reviewer, whose verdict stands.

It stays behind the ``ScreenshotWorker`` seam, so swapping ``StubScreenshotWorker`` for the
real ``GodotXvfbWorker`` changes what is *seen*, not this wiring.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from game.onepond.checks import CONFIG_NAME
from game.onepond.render import ScreenshotWorker, StubScreenshotWorker
from harness.models import CriterionVerdict, Defect, Result, Stage, Ticket, Verdict
from harness.review.base import Reviewer
from harness.review.packet_builder import ReviewPacket
from harness.review.visual_gate import ReferenceAnchoredScorer


class OnePondVisualReviewer(Reviewer):
    """Render the One Pond config, gate it visually, then defer to a base reviewer."""

    id = "onepond-visual"

    def __init__(self, base: Reviewer, *, worker: Optional[ScreenshotWorker] = None,
                 scorer: Optional[ReferenceAnchoredScorer] = None,
                 render_dir: Optional[Path] = None):
        self._base = base
        self._worker = worker or StubScreenshotWorker()
        self._scorer = scorer or ReferenceAnchoredScorer()
        self._render_dir = Path(render_dir) if render_dir else Path(
            tempfile.mkdtemp(prefix="onepond_render_"))

    def review(self, packet: ReviewPacket, ticket: Ticket) -> Verdict:
        config = self._config_from(packet)
        if config is None:
            return self._base.review(packet, ticket)  # nothing to render; defer

        try:
            import PIL  # noqa: F401  (probe: without Pillow the visual gate is simply unavailable)
        except ImportError:
            return self._base.review(packet, ticket)  # don't block a run on a missing optional dep

        try:
            self._render_dir.mkdir(parents=True, exist_ok=True)
            out = self._worker.render(config, self._render_dir / f"{packet.ticket_id}.png")
            visual = self._scorer.score(out)
        except Exception as e:  # a config that won't even render is itself a visual defect
            return self._fail(ticket, packet, f"config did not render: {e}")

        if not visual.passed:
            return self._fail(ticket, packet, "; ".join(visual.reasons) or "failed visual gate")

        return self._base.review(packet, ticket)  # CV floor passed; the subjective reviewer decides

    # -- helpers -----------------------------------------------------------------------

    def _config_from(self, packet: ReviewPacket) -> Optional[dict]:
        for rel, contents in packet.artifact_files.items():
            if rel.rsplit("/", 1)[-1] == CONFIG_NAME:
                try:
                    return json.loads(contents)
                except json.JSONDecodeError:
                    return None
        return None

    def _fail(self, ticket: Ticket, packet: ReviewPacket, detail: str) -> Verdict:
        crit = packet.criteria[0].id if packet.criteria else "-"
        per = [CriterionVerdict(id=c.id, result=Result.FAIL, evidence="") for c in packet.criteria]
        defects = [Defect(criterion=crit, severity="blocking",
                          detail=f"visual gate: {detail}", repro="onepond_visual")]
        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id=self.id,
                             per_criterion=per, defects=defects)
