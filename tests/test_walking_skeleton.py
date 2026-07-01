"""Governance tests — the walking skeleton must prove the thesis (docs/PLAN.md, Phase 0.5).

Each test maps to a numbered verification item in the plan.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.checks.base import Check
from harness.checks.builtin import NonEmptyArtifactCheck
from harness.checks.registry import Registry, certify
from harness.gatekeeper import Gatekeeper, run_regression_suite
from harness.icarus.builder import StubBuilder
from harness.loop import Loop
from harness.models import (
    CheckResult,
    CriterionVerdict,
    Result,
    Stage,
    Ticket,
    Verdict,
)
from harness.review.base import StubReviewer
from harness.review.packet_builder import (
    IsolationViolation,
    ReviewPacket,
    build_review_packet,
    _assert_isolated,
)
from harness.selfmod.validator import validate_change
from harness.states import State, commit_pending_predecessors

from conftest import make_ticket


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


def _make_loop(git_repo, registry, gatekeeper, tmp_path, *, builder, reviewer, max_rounds=3) -> Loop:
    return Loop(
        repo_root=git_repo,
        builder=builder,
        reviewer=reviewer,
        registry=registry,
        gatekeeper=gatekeeper,
        staging_root=tmp_path / "staging",
        max_rounds=max_rounds,
    )


# --- item 0: state machine graph property --------------------------------------------


def test_commit_pending_has_exactly_one_predecessor():
    # The whole "can't self-approve" guarantee reduces to this graph invariant.
    assert commit_pending_predecessors() == frozenset({State.STAGE_B_PASS})


# --- certification (crux of Stage A) --------------------------------------------------


def test_good_check_certifies():
    outcome = certify(NonEmptyArtifactCheck())
    assert outcome.certified, outcome.reason


def test_broken_check_is_not_certified(tmp_path):
    # A check that passes its own bad fixture must be rejected by certification.
    class AlwaysPass(Check):
        id = "always_pass"
        def __init__(self):
            self.targets = ["*"]
            self.good_fixtures = [NonEmptyArtifactCheck().good_fixtures[0]]
            self.bad_fixtures = [NonEmptyArtifactCheck().bad_fixtures[0]]
        def run(self, artifact_dir, ticket):
            return CheckResult(self.id, Result.PASS, "always")

    reg = Registry(tmp_path / "lock")
    reg.register(AlwaysPass())
    outcomes = reg.certify_all()
    assert not outcomes[0].certified
    assert not reg.is_certified("always_pass")
    # inert: it does not run in Stage A
    assert reg.certified_checks() == []


# --- item 1 & 2: gate is real; builder can't self-approve -----------------------------


def test_bad_artifact_fails_and_does_not_commit(git_repo, registry, gatekeeper, tmp_path):
    head_before = _head(git_repo)
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: None),          # produces nothing
        reviewer=StubReviewer(lambda r: True),         # would pass, but never reached
    )
    result = loop.run_ticket(make_ticket())
    assert not result.committed
    assert result.final_state in {State.REWORK, State.PLATEAU_ESCALATE}
    assert _head(git_repo) == head_before             # nothing committed
    assert State.COMMIT_PENDING not in result.history


def test_builder_completed_claim_does_not_commit_if_review_fails(git_repo, registry, gatekeeper, tmp_path):
    # Builder returns status=COMPLETED (a claim). Reviewer fails every round. No commit.
    head_before = _head(git_repo)
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "a bakery mesh"),
        reviewer=StubReviewer(lambda r: False),        # always rejects
        max_rounds=2,
    )
    result = loop.run_ticket(make_ticket())
    assert not result.committed
    assert _head(git_repo) == head_before
    # There is no commit path outside the Gatekeeper: the builder object exposes no such API.
    assert not hasattr(loop.builder, "commit")


def test_good_artifact_passes_and_commits(git_repo, registry, gatekeeper, tmp_path):
    head_before = _head(git_repo)
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "a good low-poly bakery"),
        reviewer=StubReviewer(lambda r: True),
    )
    result = loop.run_ticket(make_ticket())
    assert result.committed
    assert result.final_state == State.DONE
    assert _head(git_repo) != head_before             # exactly one new commit
    accepted = git_repo / "game" / "accepted" / "T-0001" / "artifact.txt"
    assert accepted.read_text() == "a good low-poly bakery"
    # decision log must NOT have entered the committed artifact tree
    assert not (git_repo / "game" / "accepted" / "T-0001" / "decision_log.jsonl").exists()


def test_reviewer_fail_then_pass_takes_two_rounds(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: f"bakery attempt {r}"),
        reviewer=StubReviewer(lambda r: r >= 1),       # FAIL round 0, PASS round 1
    )
    result = loop.run_ticket(make_ticket())
    assert result.committed
    assert result.rounds == 2


# --- default-FAIL semantics -----------------------------------------------------------


def test_pass_with_empty_evidence_is_fail(git_repo):
    t = make_ticket()
    v = Verdict.build(
        ticket=t, stage=Stage.B, reviewer_id="x",
        per_criterion=[CriterionVerdict(id="AC2", result=Result.PASS, evidence="   ")],
    )
    assert not v.passed                                # empty evidence coerces to FAIL


def test_missing_criterion_is_fail(git_repo):
    t = make_ticket()
    v = Verdict.build(ticket=t, stage=Stage.B, reviewer_id="x", per_criterion=[])
    assert not v.passed                                # silence is not approval


# --- item 3: criteria immutable (tamper) ----------------------------------------------


def test_criteria_tamper_aborts(git_repo, registry, gatekeeper, tmp_path):
    from harness.models import AcceptanceCriterion
    t = make_ticket()
    head_before = _head(git_repo)

    class TamperingBuilder(StubBuilder):
        # A builder that mutates the frozen criteria mid-iteration (goalpost-moving).
        def build(self, packet):
            packet.ticket.acceptance_criteria[1] = AcceptanceCriterion(
                id="AC2", text="RELAXED", stage=Stage.B)
            return super().build(packet)

    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=TamperingBuilder(lambda r: "art"),
        reviewer=StubReviewer(lambda r: True),
    )
    result = loop.run_ticket(t)
    assert result.final_state == State.ABORTED_TAMPER
    assert not result.committed
    assert _head(git_repo) == head_before


def test_verdict_for_wrong_spec_is_rejected(git_repo, registry, gatekeeper, tmp_path):
    # A verdict whose criteria_hash doesn't match the frozen ticket must abort at the gate.
    t = make_ticket()
    staging = tmp_path / "s"
    staging.mkdir()
    (staging / "artifact.txt").write_text("art")
    a_results = registry.run_stage_a(staging, t)
    bad_verdict = Verdict.build(
        ticket=t, stage=Stage.B, reviewer_id="x",
        per_criterion=[CriterionVerdict(id="AC2", result=Result.PASS, evidence="ok")],
    )
    object.__setattr__(bad_verdict, "criteria_hash", "deadbeef")  # forge mismatch
    from harness.gatekeeper import GateAborted
    with pytest.raises(GateAborted):
        gatekeeper.try_commit(ticket=t, staging_dir=staging, registry=registry,
                              stage_a_results=a_results, verdict_b=bad_verdict)


# --- item 4: ratchet catches a reintroduced defect ------------------------------------


def test_ratchet_catches_reintroduced_defect(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "good bakery"),
        reviewer=StubReviewer(lambda r: True),
    )
    assert loop.run_ticket(make_ticket()).committed
    # suite is green right after acceptance
    assert run_regression_suite(gatekeeper, registry) == []

    # reintroduce the defect in the committed artifact (empty it out)
    accepted = git_repo / "game" / "accepted" / "T-0001" / "artifact.txt"
    accepted.write_text("")
    regressions = run_regression_suite(gatekeeper, registry)
    assert regressions
    assert any("T-0001" in r for r in regressions)


# --- item 4b: the ratchet is a GATE, not just a storage invariant ---------------------


def _pass_verdict(t) -> Verdict:
    return Verdict.build(ticket=t, stage=Stage.B, reviewer_id="x",
                         per_criterion=[CriterionVerdict(id="AC2", result=Result.PASS, evidence="ok")])


def _stage_a_quality(q: float) -> list[CheckResult]:
    return [CheckResult("non_empty_artifact", Result.PASS, "ok", metrics={"quality": q})]


def _staging_with(tmp_path: Path, tag: str) -> Path:
    s = tmp_path / f"stg_{tag}"
    s.mkdir()
    (s / "artifact.txt").write_text(tag)
    return s


def test_ratchet_floor_gate_blocks_regressed_recommit(git_repo, registry, gatekeeper, tmp_path):
    # "Ratchet holds": an artifact that measures WORSE than an established floor is refused
    # before it can touch the protected tree, even though both stages pass. This is the
    # enforcement half of the monotonic ratchet — previously check_floors was never called.
    t = make_ticket()
    good = gatekeeper.try_commit(ticket=t, staging_dir=_staging_with(tmp_path, "v1"),
                                 registry=registry, stage_a_results=_stage_a_quality(10.0),
                                 verdict_b=_pass_verdict(t))
    assert good.committed
    assert gatekeeper.ratchet.floors()["T-0001.quality"] == 10.0
    head_after_good = _head(git_repo)

    bad = gatekeeper.try_commit(ticket=t, staging_dir=_staging_with(tmp_path, "v2"),
                                registry=registry, stage_a_results=_stage_a_quality(3.0),
                                verdict_b=_pass_verdict(t))
    assert not bad.committed
    assert "floor" in bad.reason and "quality" in bad.reason
    assert gatekeeper.ratchet.floors()["T-0001.quality"] == 10.0      # floor never lowered
    assert _head(git_repo) == head_after_good                         # no new commit
    assert (gatekeeper.accepted_root / "T-0001" / "artifact.txt").read_text() == "v1"  # untouched


def test_ratchet_floor_gate_allows_equal_or_better(git_repo, registry, gatekeeper, tmp_path):
    t = make_ticket()
    assert gatekeeper.try_commit(ticket=t, staging_dir=_staging_with(tmp_path, "a"),
                                 registry=registry, stage_a_results=_stage_a_quality(5.0),
                                 verdict_b=_pass_verdict(t)).committed
    better = gatekeeper.try_commit(ticket=t, staging_dir=_staging_with(tmp_path, "b"),
                                   registry=registry, stage_a_results=_stage_a_quality(8.0),
                                   verdict_b=_pass_verdict(t))
    assert better.committed                                           # not a regression
    assert gatekeeper.ratchet.floors()["T-0001.quality"] == 8.0       # floor rose


# --- item 5: self-mod safety ----------------------------------------------------------


def _accept_one(loop, tid="T-0001"):
    assert loop.run_ticket(make_ticket(tid)).committed


def test_selfmod_blocks_change_that_reddens_suite(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "good bakery"),
        reviewer=StubReviewer(lambda r: True),
    )
    _accept_one(loop)
    # a "harness change" that breaks a committed artifact must be rejected
    (git_repo / "game" / "accepted" / "T-0001" / "artifact.txt").write_text("")
    res = validate_change(registry=registry, gatekeeper=gatekeeper,
                          changed_paths=["harness/loop.py", "harness/HARNESS_CHANGELOG.md"])
    assert not res.ok
    assert any("regression suite" in r for r in res.reasons)


def test_selfmod_rejects_uncertified_check(git_repo, gatekeeper, tmp_path):
    class Broken(Check):
        id = "broken"
        def __init__(self):
            self.targets = ["*"]
            self.good_fixtures = [NonEmptyArtifactCheck().good_fixtures[0]]
            self.bad_fixtures = [NonEmptyArtifactCheck().bad_fixtures[0]]
        def run(self, artifact_dir, ticket):
            return CheckResult(self.id, Result.PASS, "always passes even bad fixtures")

    reg = Registry(tmp_path / "lock2")
    reg.register(NonEmptyArtifactCheck())
    reg.register(Broken())
    res = validate_change(registry=reg, gatekeeper=gatekeeper,
                          changed_paths=["harness/checks/builtin.py", "harness/HARNESS_CHANGELOG.md"])
    assert not res.ok
    assert any("broken" in r for r in res.reasons)


def test_selfmod_requires_changelog(registry, gatekeeper):
    res = validate_change(registry=registry, gatekeeper=gatekeeper,
                          changed_paths=["harness/loop.py"])  # no changelog entry
    assert not res.ok
    assert any("HARNESS_CHANGELOG" in r for r in res.reasons)


def test_selfmod_blocks_silent_floor_drop(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "good bakery"),
        reviewer=StubReviewer(lambda r: True),
    )
    _accept_one(loop)
    prev = dict(gatekeeper.ratchet.floors())
    # silently lower a floor (no baseline_reset logged)
    metric = next(iter(prev))
    floors = gatekeeper.ratchet.floors()
    floors[metric] = prev[metric] - 1
    gatekeeper.ratchet.floors_path.write_text(__import__("json").dumps(floors))
    res = validate_change(registry=registry, gatekeeper=gatekeeper,
                          changed_paths=["harness/HARNESS_CHANGELOG.md"], prev_floors=prev)
    assert not res.ok
    assert any("floor" in r for r in res.reasons)


def test_selfmod_allows_clean_change(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=StubBuilder(lambda r: "good bakery"),
        reviewer=StubReviewer(lambda r: True),
    )
    _accept_one(loop)
    prev = dict(gatekeeper.ratchet.floors())
    res = validate_change(registry=registry, gatekeeper=gatekeeper,
                          changed_paths=["harness/loop.py", "harness/HARNESS_CHANGELOG.md"],
                          prev_floors=prev)
    assert res.ok, res.reasons


# --- item 6: reviewer isolation -------------------------------------------------------


def test_review_packet_excludes_decision_log(git_repo, tmp_path):
    t = make_ticket()
    staging = tmp_path / "s"
    staging.mkdir()
    (staging / "artifact.txt").write_text("a bakery")
    (staging / "decision_log.jsonl").write_text('{"rationale":"builder secrets"}\n')
    packet = build_review_packet(ticket=t, artifact_dir=staging)
    assert "artifact.txt" in packet.artifact_files
    assert "decision_log.jsonl" not in packet.artifact_files
    # provenance is exactly the whitelist
    assert all(p.split(":", 1)[0] in {"artifact", "criteria_hash", "rubric", "reference"}
               for p in packet.provenance)


def test_isolation_assertion_rejects_forbidden_provenance():
    bad = ReviewPacket(
        ticket_id="T", criteria_hash="h", stage=Stage.B, criteria=[], rubric_text="",
        reference_paths=[], artifact_files={},
        provenance={"decision_log:leak"},
    )
    with pytest.raises(IsolationViolation):
        _assert_isolated(bad)


def test_review_packet_rejects_unfrozen_ticket(tmp_path):
    t = make_ticket(freeze=False)
    staging = tmp_path / "s"
    staging.mkdir()
    (staging / "artifact.txt").write_text("art")
    with pytest.raises(IsolationViolation):
        build_review_packet(ticket=t, artifact_dir=staging)
