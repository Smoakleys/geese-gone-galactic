"""Phase 3.5 governance tests — text-to-3D worker seam + measured selection.

No GPU is available here, so these prove the *structure* that keeps the GPU dependency from
ever blocking or degrading the pipeline:
  * the curated pack always produces a gate-passing asset (guaranteed fallback);
  * a stub GPU worker's quality flows through to the visual gate (good passes, bad fails);
  * selection picks the first candidate that passes the reference-anchored gate;
  * selection falls back to the curated pack when every candidate fails, and says so.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PIL")

from harness.gen3d.select import select_generator
from harness.gen3d.worker import CuratedPackWorker, ProceduralStubWorker
from harness.review.visual_gate import ReferenceAnchoredScorer

REF = Path(__file__).parent / "fixtures" / "visual" / "reference.png"


def test_curated_pack_always_produces_passing_asset(tmp_path):
    worker = CuratedPackWorker()
    asset = worker.generate("a low-poly bakery", tmp_path / "out")
    assert Path(asset.mesh_path).exists() and Path(asset.preview_path).exists()
    assert ReferenceAnchoredScorer().score(Path(asset.preview_path), REF).passed


def test_curated_pack_matches_prompt_tag(tmp_path):
    asset = CuratedPackWorker().generate("build a hut please", tmp_path / "o")
    assert "hut" in asset.tags


def test_stub_worker_quality_flows_to_gate(tmp_path):
    good = ProceduralStubWorker("good-gpu", quality=1.0).generate("bakery", tmp_path / "g")
    bad = ProceduralStubWorker("bad-gpu", quality=0.1).generate("bakery", tmp_path / "b")
    scorer = ReferenceAnchoredScorer()
    assert scorer.score(Path(good.preview_path), REF).passed
    assert not scorer.score(Path(bad.preview_path), REF).passed


def test_selection_prefers_passing_candidate(tmp_path):
    result = select_generator(
        candidates=[ProceduralStubWorker("good-gpu", quality=1.0)],
        fallback=CuratedPackWorker(),
        prompt="a low-poly bakery", out_root=tmp_path / "sel", reference=REF,
    )
    assert result.passed and not result.fell_back
    assert result.worker_id == "good-gpu"


def test_selection_falls_back_to_curated_when_all_fail(tmp_path):
    result = select_generator(
        candidates=[ProceduralStubWorker("bad-gpu", quality=0.0)],
        fallback=CuratedPackWorker(),
        prompt="a low-poly bakery", out_root=tmp_path / "sel", reference=REF,
    )
    assert result.fell_back
    assert result.worker_id == "curated-pack"
    assert result.passed  # curated fallback still yields shippable art
    assert Path(result.asset.preview_path).exists()


def test_selection_first_passing_candidate_wins(tmp_path):
    # a bad GPU first, a good GPU second -> the good one is selected, no fallback
    result = select_generator(
        candidates=[
            ProceduralStubWorker("bad-gpu", quality=0.0),
            ProceduralStubWorker("good-gpu", quality=1.0),
        ],
        fallback=CuratedPackWorker(),
        prompt="bakery", out_root=tmp_path / "sel", reference=REF,
    )
    assert result.worker_id == "good-gpu" and not result.fell_back
