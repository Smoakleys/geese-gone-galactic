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


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_agentbuilder_gdscript_commits_through_full_loop(tmp_path, git_repo):
    # THE CAPSTONE: Icarus (AgentBuilder) -> Stage A (godot_parse) -> Stage B (reviewer) ->
    # Gatekeeper COMMIT. Proves the agent's work flows through the whole gate to a committed artifact.
    from harness.gatekeeper import Gatekeeper
    from harness.loop import Loop
    from harness.review.base import StubReviewer
    from game.godot.checks import GodotParseCheck

    registry = Registry(tmp_path / "lock")
    registry.register(GodotParseCheck())
    registry.certify_all()
    ticket = Ticket(
        id="T-GD-CAP", title="a Godot 4 scene.gd", kind=TicketKind.SYSTEM,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC1", text="scene.gd parses", stage=Stage.A, check_hint="godot_parse"),
            AcceptanceCriterion(id="AC2", text="reads as a scene", stage=Stage.B, rubric_ref="x"),
        ])
    ticket.freeze()
    replies = [
        "```tool\nname: write_file\npath: scene.gd\nbody:\n"
        "extends Node3D\nfunc _ready() -> void:\n\tadd_child(Camera3D.new())\n```",
        "```tool\nname: finish\nsummary: done\n```",
    ]
    loop = Loop(
        repo_root=git_repo, builder=AgentBuilder(ScriptedAgentModel(replies)),
        reviewer=StubReviewer(lambda r: True), registry=registry,
        gatekeeper=Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet"),
        staging_root=tmp_path / "staging", max_rounds=2)
    result = loop.run_ticket(ticket)
    assert result.committed, result


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_agentbuilder_scene_commits_through_render_gate(tmp_path, git_repo):
    # A rendering scene must clear BOTH godot_parse AND the new godot_render gate to commit -- proves the
    # render-quality check is enforced in the real commit path (a blank scene would be rejected here).
    from harness.gatekeeper import Gatekeeper
    from harness.loop import Loop
    from harness.review.base import StubReviewer
    from game.godot.checks import GodotParseCheck, GodotRenderCheck

    registry = Registry(tmp_path / "lock")
    registry.register(GodotParseCheck())
    registry.register(GodotRenderCheck())
    registry.certify_all()
    ticket = Ticket(
        id="T-POND-RENDER", title="a Godot pond scene.gd that renders", kind=TicketKind.SYSTEM,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC1", text="renders a visible scene", stage=Stage.A, check_hint="godot_render"),
            AcceptanceCriterion(id="AC2", text="reads as a pond", stage=Stage.B, rubric_ref="x"),
        ])
    ticket.freeze()
    scene = (
        "extends Node3D\n"
        "func _ready() -> void:\n"
        "\tvar c = Camera3D.new()\n"
        "\tadd_child(c)\n"
        "\tc.position = Vector3(6, 6, 6)\n"
        "\tc.look_at(Vector3.ZERO, Vector3.UP)\n"
        "\tc.projection = Camera3D.PROJECTION_ORTHOGONAL\n"
        "\tc.size = 8\n"
        "\tc.current = true\n"
        "\tvar p = PlaneMesh.new()\n"
        "\tp.size = Vector2(8, 8)\n"
        "\tvar m = StandardMaterial3D.new()\n"
        "\tm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED\n"
        '\tm.albedo_color = Color("green")\n'
        "\tvar mi = MeshInstance3D.new()\n"
        "\tmi.mesh = p\n"
        "\tmi.material_override = m\n"
        "\tadd_child(mi)\n"
        # a blue pond -> a real multi-element scene (land + water), clearing the distinct-colours bar
        "\tvar p2 = PlaneMesh.new()\n"
        "\tp2.size = Vector2(3, 3)\n"
        "\tvar m2 = StandardMaterial3D.new()\n"
        "\tm2.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED\n"
        '\tm2.albedo_color = Color("blue")\n'
        "\tvar mi2 = MeshInstance3D.new()\n"
        "\tmi2.mesh = p2\n"
        "\tmi2.material_override = m2\n"
        "\tmi2.position = Vector3(0, 0.1, 0)\n"
        "\tadd_child(mi2)\n"
    )
    replies = [
        "```tool\nname: write_file\npath: scene.gd\nbody:\n" + scene + "```",
        "```tool\nname: finish\nsummary: done\n```",
    ]
    loop = Loop(
        repo_root=git_repo, builder=AgentBuilder(ScriptedAgentModel(replies)),
        reviewer=StubReviewer(lambda r: True), registry=registry,
        gatekeeper=Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet"),
        staging_root=tmp_path / "staging", max_rounds=2)
    result = loop.run_ticket(ticket)
    assert result.committed, result
