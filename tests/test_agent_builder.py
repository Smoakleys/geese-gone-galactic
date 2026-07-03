"""Offline tests for AgentBuilder — Icarus's agent runtime behind the harness Builder seam."""

from __future__ import annotations

from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.agent_builder import AgentBuilder, task_from_packet
from harness.models import (
    AcceptanceCriterion,
    BuildPacket,
    BuildStatus,
    Defect,
    Stage,
    Ticket,
    TicketKind,
)


def _packet(tmp_path, title="make hello.py print HI"):
    t = Ticket(id="T1", title=title, kind=TicketKind.SYSTEM, acceptance_criteria=[])
    return BuildPacket(ticket=t, writable_root=str(tmp_path))


def test_agent_builder_completes_and_logs(tmp_path):
    replies = [
        '```tool\nname: write_file\npath: hello.py\nbody:\nprint("HI")\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    res = AgentBuilder(ScriptedAgentModel(replies)).build(_packet(tmp_path))
    assert res.status == BuildStatus.COMPLETED
    assert (tmp_path / "hello.py").exists()
    assert (tmp_path / "decision_log.jsonl").exists()


def test_agent_builder_gave_up_when_no_files(tmp_path):
    replies = ['```tool\nname: finish\nsummary: produced nothing\n```']
    res = AgentBuilder(ScriptedAgentModel(replies)).build(_packet(tmp_path))
    assert res.status == BuildStatus.GAVE_UP
    assert (tmp_path / "decision_log.jsonl").exists()  # log still written


def test_agent_builder_id_reflects_model():
    b = AgentBuilder(ScriptedAgentModel([]))
    assert b.id.startswith("icarus-agent:")


def test_task_from_packet_includes_criteria_and_defects(tmp_path):
    crit = AcceptanceCriterion(id="AC1", text="prints HI", stage=Stage.A)
    t = Ticket(id="T", title="do X", kind=TicketKind.SYSTEM, acceptance_criteria=[crit])
    pkt = BuildPacket(
        ticket=t, writable_root=str(tmp_path),
        defects=[Defect(criterion="c", severity="blocking", detail="was blank", repro="r")],
    )
    task = task_from_packet(pkt)
    assert "do X" in task
    assert "prints HI" in task
    assert "was blank" in task
