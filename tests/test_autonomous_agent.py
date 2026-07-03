"""The AutonomousRunner drives the REAL agent (AgentBuilder) across multiple tickets to commit.

Deterministic (scripted agent, throwaway repo): proves unattended multi-ticket operation with Icarus's
agent builder — the level above the single-ticket capstone.
"""

from __future__ import annotations

from control.runner import AutonomousRunner
from control.store import ControlMode, RunStore
from harness.checks.builtin import default_registry
from harness.gatekeeper import Gatekeeper
from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.agent_builder import AgentBuilder
from harness.models import AcceptanceCriterion, Stage, Ticket, TicketKind
from harness.review.base import StubReviewer


def _ticket(tid: str) -> Ticket:
    t = Ticket(
        id=tid, title="write solution.py", kind=TicketKind.SYSTEM,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC1", text="valid python", stage=Stage.A, check_hint="python_syntax"),
            AcceptanceCriterion(id="AC2", text="reads ok", stage=Stage.B, rubric_ref="x"),
        ])
    t.freeze()
    return t


def test_autonomous_runner_drives_agent_across_tickets(tmp_path, git_repo):
    replies = [
        '```tool\nname: write_file\npath: solution.py\nbody:\nprint(1)\n```',
        '```tool\nname: finish\nsummary: done\n```',
        '```tool\nname: write_file\npath: solution.py\nbody:\nprint(2)\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    store = RunStore(tmp_path / "state.json")
    store.set_mode(ControlMode.RUNNING)
    runner = AutonomousRunner(
        store=store, repo_root=git_repo,
        registry=default_registry(tmp_path / "lock"),
        gatekeeper=Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet"),
        reviewer=StubReviewer(lambda r: True),
        icarus_builder=AgentBuilder(ScriptedAgentModel(replies)),
        staging_root=tmp_path / "staging")
    runner.submit(_ticket("T-1"))
    runner.submit(_ticket("T-2"))

    records = runner.run_pending()
    assert len(records) == 2
    assert all(r.committed for r in records), [(r.ticket_id, r.final_state, r.committed) for r in records]
    # both accepted by Icarus (no escape hatch) -> full autonomy
    assert store.snapshot()["autonomy_rate"] == 1.0
