"""Offline tests for AgentBuilder — Icarus's agent runtime behind the harness Builder seam."""

from __future__ import annotations

from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.agent_builder import AgentBuilder, ModelRouter, task_from_packet, visual_router
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


def test_agentbuilder_logs_rework_defects_for_stage_c(tmp_path):
    from pathlib import Path

    from harness.review.decision_log_review import load_defect_records
    t = Ticket(id="T", title="do X", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    pkt = BuildPacket(ticket=t, writable_root=str(tmp_path),
                      defects=[Defect(criterion="cohesion", severity="blocking",
                                      detail="base reads as scattered", repro="r")])
    replies = ['```tool\nname: write_file\npath: x.py\nbody:\nprint(1)\n```',
               '```tool\nname: finish\nsummary: x\n```']
    res = AgentBuilder(ScriptedAgentModel(replies)).build(pkt)
    recs = load_defect_records(Path(res.decision_log_path), t.id)
    assert any(r.criterion == "cohesion" and "scattered" in r.detail for r in recs)


def test_agent_builder_gave_up_when_no_files(tmp_path):
    replies = ['```tool\nname: finish\nsummary: produced nothing\n```']
    res = AgentBuilder(ScriptedAgentModel(replies)).build(_packet(tmp_path))
    assert res.status == BuildStatus.GAVE_UP
    assert (tmp_path / "decision_log.jsonl").exists()  # log still written


def test_agent_builder_id_reflects_model():
    b = AgentBuilder(ScriptedAgentModel([]))
    assert b.id.startswith("icarus-agent:")


def _model(mid, replies):
    m = ScriptedAgentModel(replies)
    m.model_id = mid
    return m


def test_model_router_routes_visual_to_big():
    fast = _model("fast", [])
    big = _model("big", [])
    r = visual_router(fast, big)
    assert r.for_task("render a Godot scene with a Camera3D").model_id == "big"
    assert r.for_task("gdscript scene.gd").model_id == "big"
    assert r.for_task("simulate the bread economy and print the total").model_id == "fast"


def test_model_router_routes_debugging_to_big():
    # measured: the 30B fixes debugging (4/4) where the fast model doesn't (2/4) -> route fix-it to big
    fast = _model("fast", [])
    big = _model("big", [])
    r = visual_router(fast, big)
    assert r.for_task("solution.py is BROKEN; read it, fix the bug, and run it").model_id == "big"
    assert r.for_task("it has an off-by-one bug and prints the wrong value").model_id == "big"
    assert r.for_task("write code that prints the sum of two numbers").model_id == "fast"


def test_agentbuilder_router_selects_model_per_ticket(tmp_path):
    fast = _model("fast", ['```tool\nname: write_file\npath: logic.py\nbody:\nprint(1)\n```',
                           '```tool\nname: finish\nsummary: x\n```'])
    big = _model("big", ['```tool\nname: write_file\npath: scene.gd\nbody:\nextends Node3D\n```',
                         '```tool\nname: finish\nsummary: x\n```'])
    builder = AgentBuilder(router=visual_router(fast, big))
    assert builder.id.startswith("icarus-agent:routed(")

    vt = Ticket(id="V", title="render a Godot scene", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    builder.build(BuildPacket(ticket=vt, writable_root=str(tmp_path / "v")))
    assert (tmp_path / "v" / "scene.gd").exists()          # visual -> big model

    lt = Ticket(id="L", title="compute a sum", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    builder.build(BuildPacket(ticket=lt, writable_root=str(tmp_path / "l")))
    assert (tmp_path / "l" / "logic.py").exists()          # logic -> fast model


def test_agentbuilder_requires_model_or_router():
    import pytest
    with pytest.raises(ValueError):
        AgentBuilder()


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
