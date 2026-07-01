"""The honest flywheel end to end: a Stage-C proposal *becomes* the check that closes it.

`test_flywheel_turn` proved a hand-authored check closes a subjective gap. This proves the
*whole* loop the system is supposed to run unattended:

1. reviewers repeatedly reject scattered ponds with a subjective ``cohesion`` defect;
2. the live pipeline harvests those decision logs (Stage C) and surfaces a ``ProposedAdjustment``
   with a concrete ``suggested_check_id``;
3. a deterministic check authored to that proposal — same id — certifies and now gates the
   defect in Stage A, so the reviewer never has to raise it by hand again.

The key assertion is the join: the id Stage C *proposed* equals the id of the check that was
*authored*, and that check rejects the scattered pond a bare Stage A waved through.
"""

from __future__ import annotations

import json
from pathlib import Path

from control.runner import AutonomousRunner
from control.store import RunStore
from game.onepond.checks import CohesionCheck, build_onepond_registry
from harness.checks.builtin import default_registry
from harness.checks.registry import certify, stage_a_passed
from harness.gatekeeper import Gatekeeper
from harness.icarus.llm_builder import LLMBuilder, ScriptedGenerationClient
from harness.models import CriterionVerdict, Defect, Result, Stage, Verdict
from harness.review.base import Reviewer

from conftest import make_ticket

SCATTERED = {"grid": [8, 8], "start_bread": 12, "buildings": [
    {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 7, "y": 7}]}
CLUSTERED = {"grid": [8, 8], "start_bread": 12, "buildings": [
    {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 1, "y": 0}]}


class _RejectScatterAsIncoherent(Reviewer):
    """Rejects the first review of each ticket with a subjective ``cohesion`` defect, then passes.

    Models the reviewers who kept hand-rejecting scattered ponds before a deterministic gate
    existed — the exact recurring subjective defect Stage C is meant to harvest.
    """

    id = "reject-scatter"

    def __init__(self):
        self._seen: set[str] = set()

    def review(self, packet, ticket):
        first = ticket.id not in self._seen
        self._seen.add(ticket.id)
        if first:
            per = [CriterionVerdict(id=c.id, result=Result.FAIL, evidence="")
                   for c in packet.criteria]
            defects = [Defect(criterion="cohesion", severity="blocking",
                              detail="buildings scattered across the pond", repro="taste")]
            return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id="r-fail",
                                 per_criterion=per, defects=defects)
        per = [CriterionVerdict(id=c.id, result=Result.PASS, evidence=f"{c.id} ok")
               for c in packet.criteria]
        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id="r-pass", per_criterion=per)


def _artifact(tmp_path: Path, config: dict) -> Path:
    d = tmp_path / "art"
    d.mkdir(parents=True, exist_ok=True)
    (d / "onepond_config.json").write_text(json.dumps(config))
    return d


def test_cohesion_threshold_tightened_rejects_marginal_layouts(tmp_path):
    # Acting on a tighten_rubric signal: the compactness gate was raised 0.25 -> 0.5. A layout
    # the old gate passed (compactness 0.33) is now rejected, while every shipped ticket (all
    # >= 0.7 compact) still passes and the check still certifies.
    from game.onepond.checks import CohesionCheck
    from game.onepond.tickets import POND_CONFIGS
    check = CohesionCheck()
    assert check.MIN_COMPACTNESS == 0.5 and certify(check).certified

    marginal = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 2, "y": 1}]}  # 2 / (3*2) = 0.33
    res = check.run(_artifact(tmp_path / "m", marginal), make_ticket())
    assert res.result == Result.FAIL and "scattered" in res.evidence

    for tid, cfg in POND_CONFIGS.items():
        r = check.run(_artifact(tmp_path / tid, cfg), make_ticket())
        assert r.result is not Result.FAIL, f"{tid} must not fail the stricter gate (got {r.result})"


def test_stage_c_proposal_is_realized_as_the_check_that_closes_it(git_repo, tmp_path):
    # (1)+(2) The live pipeline harvests the recurring subjective defect into a proposal. Uses a
    # pre-cohesion registry (default checks only) so the scattered pond passes Stage A and the
    # 'cohesion' complaint is genuinely subjective, coming from the reviewer.
    store = RunStore(tmp_path / "state.json")
    registry = default_registry(tmp_path / "lock")
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry,
        gatekeeper=Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet"),
        reviewer=_RejectScatterAsIncoherent(),
        icarus_builder=LLMBuilder(ScriptedGenerationClient(lambda p: {
            "onepond_config.json": json.dumps(SCATTERED)})),
        staging_root=tmp_path / "staging", max_rounds=4, stage_c_threshold=3,
    )
    for tid in ("T-1", "T-2", "T-3"):
        runner.submit(make_ticket(tid))
    runner.run_pending()

    proposals = store.proposals()
    assert proposals, "the recurring cohesion defect must surface a Stage-C proposal"
    proposed_id = proposals[0]["suggested_check_id"]

    # (3) The authored check IS that proposal: same id, and it certifies.
    check = CohesionCheck()
    assert check.id == proposed_id, "the harvested check must be exactly what Stage C proposed"
    assert certify(check).certified

    # And it closes the gap: the scattered pond a bare Stage A waved through is now rejected,
    # while a clustered pond passes.
    bare = default_registry(tmp_path / "lock2")
    assert stage_a_passed(bare.run_stage_a(_artifact(tmp_path, SCATTERED), make_ticket()))
    gated = build_onepond_registry(tmp_path / "lock3")
    scattered_results = gated.run_stage_a(_artifact(tmp_path / "s", SCATTERED), make_ticket())
    assert not stage_a_passed(scattered_results)
    fail = next(r for r in scattered_results if r.check_id == proposed_id)
    assert fail.result == Result.FAIL and "scattered" in fail.evidence
    assert stage_a_passed(gated.run_stage_a(_artifact(tmp_path / "c", CLUSTERED), make_ticket()))
