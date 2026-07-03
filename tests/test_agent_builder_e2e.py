"""E2E: an artifact built by AgentBuilder (Icarus's agent runtime) flows through the gate's Stage A.

Uses a deterministic ScriptedAgentModel so the pipeline is proven with no LLM/GPU. This is the
connection between the two harnesses: agent builds -> certified checks gate it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game.godot.binary import godot_path
from harness.checks.builtin import default_registry
from harness.checks.registry import Registry, stage_a_passed
from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.agent_builder import AgentBuilder
from harness.models import AcceptanceCriterion, BuildPacket, Stage, Ticket, TicketKind


def _ticket(check_hint: str) -> Ticket:
    return Ticket(
        id="T-AGENT", title="write the required file", kind=TicketKind.SYSTEM,
        acceptance_criteria=[AcceptanceCriterion(id="AC1", text="artifact is valid",
                                                 stage=Stage.A, check_hint=check_hint)])


def test_agentbuilder_output_passes_stage_a_python(tmp_path):
    registry = default_registry(tmp_path / "lock")
    ticket = _ticket("python_syntax")
    packet = BuildPacket(ticket=ticket, writable_root=str(tmp_path / "stage"))
    replies = [
        '```tool\nname: write_file\npath: solution.py\nbody:\nprint("ok")\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    result = AgentBuilder(ScriptedAgentModel(replies)).build(packet)
    stage_a = registry.run_stage_a(Path(result.artifact_dir), ticket)
    assert stage_a_passed(stage_a), [(r.check_id, r.result.value, r.evidence) for r in stage_a]


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_agentbuilder_gdscript_passes_godot_parse(tmp_path):
    from game.godot.checks import GodotParseCheck
    registry = Registry(tmp_path / "lock")
    registry.register(GodotParseCheck())
    registry.certify_all()
    ticket = _ticket("godot_parse")
    packet = BuildPacket(ticket=ticket, writable_root=str(tmp_path / "stage"))
    replies = [
        "```tool\nname: write_file\npath: scene.gd\nbody:\n"
        "extends Node3D\nfunc _ready() -> void:\n\tadd_child(Camera3D.new())\n```",
        "```tool\nname: finish\nsummary: done\n```",
    ]
    result = AgentBuilder(ScriptedAgentModel(replies)).build(packet)
    stage_a = registry.run_stage_a(Path(result.artifact_dir), ticket)
    assert stage_a_passed(stage_a), [(r.check_id, r.result.value, r.evidence) for r in stage_a]
