"""Phase 3 governance tests — real Icarus builder + the control surface.

Proves the "runs unattended, intervention optional" contract:
  * ``LLMBuilder`` (Icarus behind a generation seam) drives the real loop to a commit and
    gives up honestly (never a silent empty commit);
  * the ``RunStore`` persists mode/heartbeat/records/metrics durably;
  * the ``AutonomousRunner`` processes a queue, auto-escalates to the escape hatch on plateau
    with no human, and stops cleanly on Pause/Stop (resumable);
  * the stdlib dashboard actually serves status + heartbeat and applies Start/Stop/Pause.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from control.dashboard import make_server, render_html
from control.runner import AutonomousRunner
from control.store import ControlMode, RunRecord, RunStore
from harness.icarus.builder import StubBuilder
from harness.icarus.llm_builder import LLMBuilder, ScriptedGenerationClient
from harness.review.base import StubReviewer
from harness.states import State

from conftest import make_ticket


# --- Icarus builder -------------------------------------------------------------------


def test_llm_builder_writes_files_and_decision_log(tmp_path):
    from harness.models import BuildPacket, BuildStatus
    client = ScriptedGenerationClient(lambda p: {"artifact.txt": "a low-poly bakery"})
    packet = BuildPacket(ticket=make_ticket(), writable_root=str(tmp_path / "s"))
    result = LLMBuilder(client).build(packet)
    assert result.status == BuildStatus.COMPLETED
    root = Path(result.artifact_dir)
    assert (root / "artifact.txt").read_text() == "a low-poly bakery"
    assert (root / "decision_log.jsonl").exists()


def test_llm_builder_gives_up_on_empty(tmp_path):
    from harness.models import BuildPacket, BuildStatus
    packet = BuildPacket(ticket=make_ticket(), writable_root=str(tmp_path / "s"))
    result = LLMBuilder(ScriptedGenerationClient(lambda p: {})).build(packet)
    assert result.status == BuildStatus.GAVE_UP  # honest give-up, no empty commit


def test_llm_builder_records_defects_for_flywheel(tmp_path):
    from harness.models import BuildPacket, Defect
    from harness.review.decision_log_review import load_defect_records
    packet = BuildPacket(
        ticket=make_ticket(), writable_root=str(tmp_path / "s"),
        defects=[Defect(criterion="AC2", severity="blocking", detail="reads as a box")],
    )
    LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "v2"})).build(packet)
    recs = load_defect_records(Path(tmp_path / "s" / "decision_log.jsonl"), "T-0001")
    assert recs and recs[0].criterion == "AC2"


# --- run store ------------------------------------------------------------------------


def test_run_store_modes_and_heartbeat(tmp_path):
    store = RunStore(tmp_path / "state.json")
    assert store.mode is ControlMode.RUNNING
    store.pause(); assert store.mode is ControlMode.PAUSED
    store.stop(); assert store.mode is ControlMode.STOPPED
    store.start(); assert store.mode is ControlMode.RUNNING
    assert store.heartbeat_age() is None
    store.beat()
    assert store.heartbeat_age() is not None and store.heartbeat_age() < 5


def test_run_store_records_and_autonomy_rate(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.record(RunRecord("T1", State.DONE.value, True, 1, escape_hatch=False))
    store.record(RunRecord("T2", State.DONE.value, True, 2, escape_hatch=True))
    assert store.metrics()["accepted"] == 2
    assert store.autonomy_rate() == 0.5
    store.record(RunRecord("T3", State.PLATEAU_ESCALATE.value, False, 3, escape_hatch=True))
    assert "T3" in store.blocked()


def test_run_store_survives_reopen(tmp_path):
    p = tmp_path / "state.json"
    RunStore(p).record(RunRecord("T1", State.DONE.value, True, 1, escape_hatch=False))
    assert RunStore(p).metrics()["accepted"] == 1  # persisted across a fresh handle


# --- autonomous runner ----------------------------------------------------------------


def _runner(store, git_repo, registry, gatekeeper, tmp_path, *, icarus, escape=None,
            plateau_window=2, max_rounds=5):
    return AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        escape_hatch_builder=escape, staging_root=tmp_path / "staging",
        plateau_window=plateau_window, max_rounds=max_rounds,
    )


def test_runner_commits_with_icarus_full_autonomy(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a crisp bakery"}))
    runner = _runner(store, git_repo, registry, gatekeeper, tmp_path, icarus=icarus)
    runner.submit(make_ticket())
    recs = runner.run_pending()
    assert recs[0].committed and not recs[0].escape_hatch
    assert store.autonomy_rate() == 1.0  # built with zero escape-hatch help


def test_runner_auto_escalates_to_escape_hatch_on_plateau(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    quitting_icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {}))   # always gives up
    escape = StubBuilder(lambda r: "escape-hatch rescued this bakery")
    runner = _runner(store, git_repo, registry, gatekeeper, tmp_path,
                     icarus=quitting_icarus, escape=escape)
    runner.submit(make_ticket())
    recs = runner.run_pending()
    assert recs[0].committed, recs[0].reason
    assert recs[0].escape_hatch, "runner must auto-escalate, not stop for a human"
    assert store.autonomy_rate() == 0.0  # accepted, but only via escape hatch


def test_runner_marks_blocked_and_moves_on_when_all_fail(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    quitting = LLMBuilder(ScriptedGenerationClient(lambda p: {}))
    # no escape hatch AND icarus never succeeds -> ticket blocked, runner does not hang
    runner = _runner(store, git_repo, registry, gatekeeper, tmp_path, icarus=quitting, escape=None)
    runner.submit(make_ticket("T-9001"))
    runner.submit(make_ticket("T-9002"))
    recs = runner.run_pending()
    assert len(recs) == 2 and not any(r.committed for r in recs)
    assert "T-9001" in store.blocked() and "T-9002" in store.blocked()


def test_runner_periodic_cold_audit_hard_blocks(git_repo, registry, gatekeeper, tmp_path):
    from harness.audit.cold_audit import AuditFinding, AuditReport
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    dirty = AuditReport(findings=[AuditFinding("T-1", "regression", "bytes changed from baseline")])
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        staging_root=tmp_path / "staging", audit_every=1, auditor=lambda: dirty)
    runner.submit(make_ticket("T-1")); runner.submit(make_ticket("T-2"))
    recs = runner.run_pending()
    assert len(recs) == 1 and recs[0].committed        # first accepted, then the audit blocked
    assert runner.pending == 1                          # second ticket never processed
    assert store.mode is ControlMode.STOPPED            # hard-block: no more acceptances
    assert store.audit()["blocked"] and store.snapshot()["audit"]["blocked"]


def test_runner_real_cold_audit_catches_corrupted_artifact(git_repo, registry, gatekeeper, tmp_path):
    # No injected auditor: the *real* cold_audit runs. Accept T-1, corrupt its committed bytes
    # behind the harness's back, then accept T-2 — the next in-loop audit must catch the T-1
    # regression and hard-block, so the runner never keeps building on a rotted tree.
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        staging_root=tmp_path / "staging", audit_every=1)  # real auditor

    runner.submit(make_ticket("T-1"))
    assert runner.run_pending()[0].committed
    assert store.mode is ControlMode.RUNNING and not store.audit()["blocked"]  # first audit clean

    (git_repo / "game" / "accepted" / "T-1" / "artifact.txt").write_text("tampered!")

    runner.submit(make_ticket("T-2"))
    recs2 = runner.run_pending()
    assert recs2[0].committed                          # T-2 itself is fine...
    assert store.audit()["blocked"]                    # ...but the real audit caught T-1's rot
    assert store.mode is ControlMode.STOPPED           # and hard-blocked further acceptances


def test_runner_periodic_cold_audit_clean_continues(git_repo, registry, gatekeeper, tmp_path):
    from harness.audit.cold_audit import AuditReport
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        staging_root=tmp_path / "staging", audit_every=1, auditor=lambda: AuditReport())
    runner.submit(make_ticket("T-1")); runner.submit(make_ticket("T-2"))
    recs = runner.run_pending()
    assert len(recs) == 2 and all(r.committed for r in recs)
    assert store.mode is ControlMode.RUNNING
    assert store.audit()["count"] == 2 and not store.audit()["blocked"]


def test_runner_respects_pause_and_resumes(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = _runner(store, git_repo, registry, gatekeeper, tmp_path, icarus=icarus)
    runner.submit(make_ticket("T-1")); runner.submit(make_ticket("T-2"))
    store.pause()
    assert runner.run_pending() == []          # paused: nothing processed
    assert runner.pending == 2                  # queue intact, resumable
    store.start()
    recs = runner.run_pending()
    assert len(recs) == 2 and all(r.committed for r in recs)


# --- stage C flywheel (decision-log harvest through the runner) -----------------------


class _RejectFirstPerTicket:
    """Reviewer that rejects the first review of each ticket with a fixed defect, then passes.

    Every ticket therefore records one identical subjective defect in its (staging-only)
    decision log, so across enough tickets Stage C sees a recurring signature.
    """

    id = "reject-first-per-ticket"

    def __init__(self):
        self._seen: set[str] = set()

    def review(self, packet, ticket):
        from harness.models import CriterionVerdict, Defect, Result, Stage, Verdict
        first = ticket.id not in self._seen
        self._seen.add(ticket.id)
        if first:
            per = [CriterionVerdict(id=c.id, result=Result.FAIL, evidence="")
                   for c in packet.criteria]
            defects = [Defect(criterion="AC2", severity="blocking",
                              detail="reads as a generic box not a bakery", repro="n/a")]
            return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id="r-fail",
                                 per_criterion=per, defects=defects)
        per = [CriterionVerdict(id=c.id, result=Result.PASS, evidence=f"{c.id} met")
               for c in packet.criteria]
        return Verdict.build(ticket=ticket, stage=Stage.B, reviewer_id="r-pass",
                             per_criterion=per)


def test_runner_stage_c_surfaces_recurring_defect_proposal(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=_RejectFirstPerTicket(), icarus_builder=icarus,
        staging_root=tmp_path / "staging", plateau_window=5, max_rounds=5,
        stage_c_threshold=3,
    )
    for tid in ("T-1", "T-2", "T-3"):
        runner.submit(make_ticket(tid))
    recs = runner.run_pending()

    assert all(r.committed for r in recs)          # each accepted on its 2nd round
    proposals = store.proposals()                  # persisted end-to-end, no manual harvest
    assert proposals, "a subjective defect recurring across tickets must yield a proposal"
    p = proposals[0]
    assert p["kind"] == "new_check"
    assert p["occurrences"] >= 3 and "AC2" in p["signature"]
    assert store.snapshot()["stage_c_proposals"]   # surfaced in the dashboard snapshot too


def test_runner_stage_c_ignores_stale_staging_from_prior_runs(git_repo, registry, gatekeeper, tmp_path):
    # In a persistent workdir, a decision log from an earlier run lingers under staging_root.
    # Harvest must scope to tickets processed THIS run, or it would re-harvest the stale defects
    # and invent a proposal for work this run never did.
    staging = tmp_path / "staging"
    stale = staging / "T-OLD"; stale.mkdir(parents=True)
    lines = "\n".join(json.dumps({"defect": {"criterion": "cohesion", "severity": "blocking",
                                             "detail": "scattered"}}) for _ in range(5))
    (stale / "decision_log.jsonl").write_text(lines + "\n")

    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        staging_root=staging, stage_c_threshold=3)
    runner.submit(make_ticket("T-1"))
    runner.run_pending()
    assert store.proposals() == []  # stale T-OLD ignored; only the clean T-1 was harvested


def test_runner_stage_c_no_proposal_below_threshold(git_repo, registry, gatekeeper, tmp_path):
    store = RunStore(tmp_path / "state.json")
    icarus = LLMBuilder(ScriptedGenerationClient(lambda p: {"artifact.txt": "a bakery"}))
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=icarus,
        staging_root=tmp_path / "staging", stage_c_threshold=3,
    )
    runner.submit(make_ticket("T-1"))
    runner.run_pending()
    assert store.proposals() == []  # clean acceptances leave no recurring defect to harvest


# --- dashboard ------------------------------------------------------------------------


def test_render_html_offline(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.beat()
    html = render_html(store)
    assert "autonomy rate" in html and "RUNNING" in html
    assert "no recurring subjective defect" in html  # empty Stage-C section renders


def test_render_html_shows_stage_c_proposals(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.record_proposals([{"kind": "new_check", "signature": "cohesion:scattered",
                             "occurrences": 4, "rationale": "...",
                             "suggested_check_id": "auto_cohesion_check"}])
    html = render_html(store)
    assert "auto_cohesion_check" in html and "cohesion:scattered" in html
    assert "stage-C proposals" in html and "new_check" in html  # kind is shown


def test_dashboard_serves_and_controls(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.beat()
    server = make_server(store, "127.0.0.1", 0)
    port = server.server_port
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        base = f"http://127.0.0.1:{port}"
        body = urllib.request.urlopen(base + "/", timeout=5).read().decode()
        assert "harness control" in body.lower()
        hb = json.loads(urllib.request.urlopen(base + "/heartbeat", timeout=5).read())
        assert "mode" in hb and hb["mode"] == "RUNNING"
        # Start/Stop/Pause actually flips the store mode.
        req = urllib.request.Request(base + "/control/pause", method="POST", data=b"")
        urllib.request.urlopen(req, timeout=5).read()
        assert store.mode is ControlMode.PAUSED
    finally:
        server.shutdown()
        server.server_close()
