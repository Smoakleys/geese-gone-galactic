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


def test_post_build_exception_does_not_crash_the_build(tmp_path):
    # A post_build hook that raises (e.g. compose_scene choking on malformed content) must NOT crash the
    # build -- it's caught and gating still runs on whatever was produced. Locks that robustness path.
    replies = ["```tool\nname: write_file\npath: content.gd\nbody:\nfunc build(root): pass\n```",
               "```tool\nname: finish\nsummary: done\n```"]

    def boom(root):
        raise ValueError("post_build compose failed")

    res = AgentBuilder(ScriptedAgentModel(replies), post_build=boom).build(_packet(tmp_path))
    assert res.status == BuildStatus.COMPLETED       # content.gd was produced; build returned, didn't crash


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


def test_model_router_routes_templated_scenes_to_fast():
    # a templated scene task (helper-based) is reliable + fast on the resident model -> route to fast,
    # even though it mentions a camera (which would otherwise hit the big model)
    fast = _model("fast", [])
    big = _model("big", [])
    r = visual_router(fast, big)
    templated = ("Write content.gd with func build(root): call add_plane and add_box. Do NOT add a Camera3D.")
    assert r.for_task(templated).model_id == "fast"
    # an OPEN-ENDED scene (no helpers) still goes to big
    assert r.for_task("render a Godot scene from scratch with a Camera3D").model_id == "big"


def test_all_onepond_tickets_route_to_the_fast_model():
    # INTEGRATION guard: every real One Pond ticket must route to FAST -- templated scenes (via the
    # template rule, which must beat the visual rule despite mentioning scene/camera/Node3D) and logic (the
    # default). A title edit that dropped the template keywords would silently mis-route a scene to the slow
    # 30B -- a real perf regression the synthetic unit tests above wouldn't catch.
    from game.onepond_tickets import one_pond_tickets
    r = visual_router(_model("fast", []), _model("big", []))
    mis = [t.id for t in one_pond_tickets() if r.for_task(t.title).model_id != "fast"]
    assert not mis, f"tickets mis-routed to the slow big model: {mis}"


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


def test_agentbuilder_runs_post_build_hook(tmp_path):
    from pathlib import Path
    calls = []

    def hook(root):
        calls.append(root)
        (Path(root) / "scene.gd").write_text("extends Node3D\n")

    replies = ['```tool\nname: write_file\npath: content.gd\nbody:\nfunc build(root):\n\tpass\n```',
               '```tool\nname: finish\nsummary: x\n```']
    t = Ticket(id="T", title="t", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    AgentBuilder(ScriptedAgentModel(replies), post_build=hook).build(
        BuildPacket(ticket=t, writable_root=str(tmp_path)))
    assert calls and (tmp_path / "scene.gd").exists()


def test_materialize_templated_scene_composes_and_is_noop_when_present(tmp_path):
    from game.godot.scene_template import materialize_templated_scene
    (tmp_path / "content.gd").write_text("func build(root: Node3D) -> void:\n\tpass\n")
    materialize_templated_scene(tmp_path)
    scene = (tmp_path / "scene.gd").read_text()
    assert "extends Node3D" in scene and "Camera3D" in scene and "func build" in scene
    assert not (tmp_path / "content.gd").exists()         # incomplete source removed (would fail parse)
    materialize_templated_scene(tmp_path)                 # no-op now that scene.gd exists
    assert (tmp_path / "scene.gd").read_text() == scene


def test_compose_scene_avoids_duplicate_helper_defs():
    # a local model sometimes redefines add_plane/add_box despite instructions; duplicate function defs
    # are a Godot parse error that blanks the render, so compose must not inject the template's copies.
    from game.godot.scene_template import compose_scene
    content = ("func add_plane(root, size, color, y=0.0):\n\tpass\n"
               "func build(root: Node3D) -> void:\n\tadd_plane(root, Vector2(4, 4), Color.GREEN)\n")
    scene = compose_scene(content)
    assert scene.count("func add_plane") == 1     # not duplicated
    assert "func _ready" in scene                 # camera template always present


def test_compose_scene_sanitizes_preload_and_prefixed_helper_calls():
    from game.godot.scene_template import compose_scene
    content = ('func build(root):\n\tvar h = preload("res://helpers.gd").new()\n'
               '\th.add_plane(root, Vector2(4, 4), Color.GREEN)\n'
               '\tadd_box(root, 1.0, Color.RED, Vector3(0, 0, 0))\n')
    scene = compose_scene(content)
    assert "preload(" not in scene                 # bogus helper preload dropped
    assert "h.add_plane" not in scene and "add_plane(root" in scene   # prefix stripped to a direct call


def test_compose_scene_strips_python_keyword_arguments():
    # GDScript has no kwargs; a small model writes add_plane(..., y=0.1) which is a parse error.
    from game.godot.scene_template import compose_scene
    build = compose_scene("func build(root):\n\tadd_plane(root, Vector2(4, 4), Color.GREEN, y=0.1)\n")
    body = build.split("func build")[1]
    assert "y=" not in body and "0.1" in body      # keyword name stripped, value kept positionally


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
