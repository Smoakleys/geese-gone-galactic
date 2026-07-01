"""Measured generator selection with a guaranteed curated fallback.

The Phase-3.5 decision "which text-to-3D generator do we trust?" is answered by *measurement*,
not by faith in a model's reputation: run each candidate, score its preview with the same
reference-anchored visual gate Stage B uses, and take the first that passes. If none pass, use
the curated pack — art the harness can always ship — and report that we fell back so the
autonomy/quality dashboards can see a real generator is still needed.

This keeps the risky external dependency (a GPU model of unknown quality) from ever blocking
the pipeline: the worst case is a curated asset, never a stall and never junk waved through.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from harness.gen3d.worker import Asset, MeshGenerator
from harness.review.visual_gate import ReferenceAnchoredScorer


@dataclass
class SelectionResult:
    worker_id: str
    asset: Asset
    passed: bool
    score: float
    fell_back: bool
    reasons: list[str] = field(default_factory=list)


def select_generator(
    *,
    candidates: Sequence[MeshGenerator],
    fallback: MeshGenerator,
    prompt: str,
    out_root: Path,
    reference: Optional[Path] = None,
    scorer: Optional[ReferenceAnchoredScorer] = None,
) -> SelectionResult:
    """Return the first candidate whose preview passes the visual gate, else the fallback.

    Every candidate is measured against ``reference`` with ``scorer`` (default
    ``ReferenceAnchoredScorer``). The fallback is used only if no candidate passes; its own
    score is still reported for the dashboard.
    """
    scorer = scorer or ReferenceAnchoredScorer()
    out_root = Path(out_root)

    for worker in candidates:
        asset = worker.generate(prompt, out_root / worker.model_id)
        verdict = scorer.score(Path(asset.preview_path), reference)
        if verdict.passed:
            return SelectionResult(worker.model_id, asset, True, verdict.score, False)

    asset = fallback.generate(prompt, out_root / fallback.model_id)
    verdict = scorer.score(Path(asset.preview_path), reference)
    return SelectionResult(fallback.model_id, asset, verdict.passed, verdict.score,
                           True, verdict.reasons)
