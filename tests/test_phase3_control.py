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


# --- dashboard ------------------------------------------------------------------------


def test_render_html_offline(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.beat()
    html = render_html(store)
    assert "autonomy rate" in html and "RUNNING" in html


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
