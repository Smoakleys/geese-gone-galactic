"""Phase 2 governance tests — reviewers + the four anti-complacency teeth.

Covers, mapping to docs/EXECUTION_PLAN.md verification items 7 & 8:
  * a real reviewer behind the ChatClient seam, still default-FAIL / evidence-required;
  * multi-model consensus that fails closed and catches a single-model wrong verdict (item 7);
  * a decomposed, reference-anchored visual gate validated on a labeled good/bad set (item 7);
  * plateau detection as an independent escalation trigger, not just the max-rounds ceiling (8);
  * cold audits that hard-block on a regressed/ re-rejected committed artifact (item 8);
  * the decision-log -> new-check flywheel (tooth #2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.audit.cold_audit import cold_audit
from harness.loop import Loop
from harness.metrics.plateau import PlateauDetector
from harness.models import Defect
from harness.review.base import StubReviewer
from harness.review.consensus import ConsensusReviewer
from harness.review.decision_log_review import (
    DecisionLogReview,
    DefectRecord,
    load_defect_records,
)
from harness.review.llm_reviewer import LLMReviewer
from harness.review.model_client import (
    CriterionQuestion,
    ModelRequest,
    ScriptedChatClient,
    _parse_answers,
    always_pass_client,
)
from harness.review.packet_builder import build_review_packet
from harness.states import State

from conftest import make_ticket

VIS = Path(__file__).parent / "fixtures" / "visual"


def _make_loop(git_repo, registry, gatekeeper, tmp_path, *, builder, reviewer,
               max_rounds=3, plateau_window=3):
    from harness.icarus.builder import StubBuilder  # noqa: F401 (type hint clarity)
    return Loop(
        repo_root=git_repo, builder=builder, reviewer=reviewer, registry=registry,
        gatekeeper=gatekeeper, staging_root=tmp_path / "staging",
        max_rounds=max_rounds, plateau_window=plateau_window,
    )


def _packet(tmp_path, text="a low-poly bakery"):
    art = tmp_path / "art"
    art.mkdir(exist_ok=True)
    (art / "artifact.txt").write_text(text)
    t = make_ticket()
    return build_review_packet(ticket=t, artifact_dir=art), t


# --- model-client seam + LLM reviewer -------------------------------------------------


def test_parse_answers_defaults_missing_and_evidenceless_to_fail():
    req = ModelRequest(ticket_id="T", criteria_hash="h", system="",
                       questions=[CriterionQuestion("AC2", "reads as a bakery")])
    assert _parse_answers("AC2: PASS — clear bakery form", req)[0].passed
    assert not _parse_answers("AC2: FAIL — looks generic", req)[0].passed
    assert not _parse_answers("unrelated blather", req)[0].passed       # missing -> FAIL
    assert not _parse_answers("AC2: PASS", req)[0].passed               # no evidence -> FAIL


def test_llm_reviewer_pass_and_fail(tmp_path):
    packet, t = _packet(tmp_path)
    ok = LLMReviewer(ScriptedChatClient(lambda r: {"AC2": (True, "clear bakery silhouette")}))
    assert ok.review(packet, t).passed
    no = LLMReviewer(ScriptedChatClient(lambda r: {"AC2": (False, "reads as a generic box")}))
    v = no.review(packet, t)
    assert not v.passed and v.defects


def test_llm_reviewer_pass_without_evidence_is_fail(tmp_path):
    packet, t = _packet(tmp_path)
    rev = LLMReviewer(ScriptedChatClient(lambda r: {"AC2": (True, "   ")}))
    assert not rev.review(packet, t).passed  # evidence-required survives the seam


def test_llm_reviewer_mints_fresh_id_per_round(tmp_path):
    packet, t = _packet(tmp_path)
    rev = LLMReviewer(always_pass_client("m"))
    a = rev.review(packet, t).reviewer_id
    b = rev.review(packet, t).reviewer_id
    assert a != b and a.endswith("#r0") and b.endswith("#r1")


# --- multi-model consensus (item 7) ---------------------------------------------------


def test_consensus_unanimous_passes(tmp_path):
    packet, t = _packet(tmp_path)
    rev = ConsensusReviewer([always_pass_client("m1"), always_pass_client("m2")])
    assert rev.review(packet, t).passed


def test_consensus_single_dissent_fails_closed(tmp_path):
    # One model wrongly PASSes; a dissenting model must sink the verdict (catch the blind spot).
    packet, t = _packet(tmp_path)
    dissenter = ScriptedChatClient(lambda r: {"AC2": (False, "off-model proportions")}, "m2")
    rev = ConsensusReviewer([always_pass_client("m1"), dissenter])
    v = rev.review(packet, t)
    assert not v.passed
    assert any("disagreement" in d.detail for d in v.defects)


def test_consensus_cannot_manufacture_a_pass(tmp_path):
    # Neither model attests -> FAIL; adding models can only tighten, never loosen.
    packet, t = _packet(tmp_path)
    fail = ScriptedChatClient(lambda r: {}, "mX")
    assert not ConsensusReviewer([fail, fail]).review(packet, t).passed


# --- visual gate on a labeled set (item 7) --------------------------------------------


def test_visual_gate_classifies_labeled_set_perfectly():
    from harness.review.visual_gate import ReferenceAnchoredScorer, evaluate_labeled_set
    pytest.importorskip("PIL")
    scorer = ReferenceAnchoredScorer()
    res = evaluate_labeled_set(scorer, VIS, reference=VIS / "reference.png")
    assert res.total >= 6
    assert res.accuracy == 1.0, f"false_pass={res.false_pass} false_fail={res.false_fail}"
    assert res.false_pass == [], "a blind spot: bad art wrongly PASSed"


def test_visual_gate_reference_anchoring_rejects_off_model():
    from harness.review.visual_gate import ReferenceAnchoredScorer
    pytest.importorskip("PIL")
    scorer = ReferenceAnchoredScorer()
    ref = VIS / "reference.png"
    assert scorer.score(VIS / "good" / "bakery_a.png", ref).passed
    assert not scorer.score(VIS / "bad" / "blank.png", ref).passed
    assert not scorer.score(VIS / "bad" / "noise.png", ref).passed
    assert not scorer.score(VIS / "bad" / "wrong_palette.png", ref).passed
    assert not scorer.score(VIS / "bad" / "tiny.png", ref).passed


# --- plateau detection (item 8) -------------------------------------------------------


def test_plateau_detector_fires_on_stuck_signature():
    d = PlateauDetector(window=3)
    d.record(signature="X"); d.record(signature="X")
    assert not d.plateaued()
    d.record(signature="X")
    assert d.plateaued()


def test_plateau_detector_ignores_moving_target():
    d = PlateauDetector(window=3)
    for s in ("A", "B", "C"):
        d.record(signature=s)
    assert not d.plateaued()


def test_plateau_detector_no_score_gain():
    d = PlateauDetector(window=3, min_gain=0.05)
    for i, s in enumerate((0.50, 0.50, 0.51)):
        d.record(signature=f"sig{i}", score=s)  # distinct sigs so only the score gate can fire
    assert d.plateaued()


def test_loop_escalates_on_plateau_before_max_rounds(git_repo, registry, gatekeeper, tmp_path):
    from harness.icarus.builder import StubBuilder
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: None),          # always produces nothing -> same defect
        reviewer=StubReviewer(lambda r: True),
        max_rounds=10, plateau_window=3,
    )
    result = loop.run_ticket(make_ticket())
    assert result.final_state == State.PLATEAU_ESCALATE
    assert result.rounds == 3, "plateau must fire at the window, not wait for max_rounds"
    assert "stuck" in result.reason


# --- cold audit (item 8) --------------------------------------------------------------


def _accept_text(git_repo, registry, gatekeeper, tmp_path, text="a good low-poly bakery"):
    from harness.icarus.builder import StubBuilder
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: text), reviewer=StubReviewer(lambda r: True),
    )
    assert loop.run_ticket(make_ticket()).committed


def test_cold_audit_clean_when_untouched(git_repo, registry, gatekeeper, tmp_path):
    _accept_text(git_repo, registry, gatekeeper, tmp_path)
    report = cold_audit(gatekeeper, registry)
    assert not report.blocked, report.summary()


def test_cold_audit_hard_blocks_on_regressed_artifact(git_repo, registry, gatekeeper, tmp_path):
    _accept_text(git_repo, registry, gatekeeper, tmp_path)
    (git_repo / "game" / "accepted" / "T-0001" / "artifact.txt").write_text("")  # rot it
    report = cold_audit(gatekeeper, registry)
    assert report.blocked
    assert any(f.kind == "regression" for f in report.findings)


def test_cold_audit_hard_blocks_on_cold_re_review(git_repo, registry, gatekeeper, tmp_path):
    _accept_text(git_repo, registry, gatekeeper, tmp_path)
    report = cold_audit(
        gatekeeper, registry,
        reviewer=StubReviewer(lambda r: False),           # a fresh cold reviewer now rejects it
        ticket_provider=lambda tid: make_ticket(tid),
    )
    assert report.blocked
    assert any(f.kind == "review" for f in report.findings)


# --- decision-log -> new-check flywheel (tooth #2) ------------------------------------


def test_decision_log_review_proposes_check_for_recurring_defect():
    detail = "reads as a generic blob, not a bakery"
    recs = [DefectRecord(f"T{i}", "AC2", detail) for i in range(3)]
    props = DecisionLogReview(threshold=3).analyze(recs)
    assert props and props[0].kind == "new_check"
    assert props[0].occurrences == 3
    assert props[0].suggested_check_id.startswith("auto_")


def test_decision_log_review_ignores_one_off():
    recs = [DefectRecord("T1", "AC2", "unique nitpick")]
    assert DecisionLogReview(threshold=3).analyze(recs) == []


def test_load_defect_records_from_log(tmp_path):
    log = tmp_path / "decision_log.jsonl"
    log.write_text(
        json.dumps({"step": "compose"}) + "\n"
        + json.dumps({"defect": {"criterion": "AC2", "detail": "off-model"}}) + "\n"
    )
    recs = load_defect_records(log, "T-0001")
    assert len(recs) == 1 and recs[0].criterion == "AC2" and recs[0].ticket_id == "T-0001"


# --- integration: real reviewer drives the real loop to a commit ----------------------


def test_llm_reviewer_drives_loop_to_commit(git_repo, registry, gatekeeper, tmp_path):
    from harness.icarus.builder import StubBuilder
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "a crisp low-poly bakery"),
        reviewer=LLMReviewer(always_pass_client("opus-sim")),
    )
    result = loop.run_ticket(make_ticket())
    assert result.committed and result.final_state == State.DONE
