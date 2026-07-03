"""The authored One Pond ticket backlog is well-formed and references real certified gates."""

from __future__ import annotations

from game.onepond_tickets import one_pond_tickets
from harness.models import Stage


def test_one_pond_tickets_well_formed_and_reference_real_gates():
    tickets = one_pond_tickets()
    assert [t.id for t in tickets] == ["OP-1", "OP-2", "OP-3", "OP-4", "OP-5", "OP-6"]
    # Stage-A hints must name checks that actually exist and are certified elsewhere in the suite.
    real_stage_a_checks = {"godot_parse", "godot_render", "python_syntax", "json_valid"}
    for t in tickets:
        stages = {c.stage for c in t.acceptance_criteria}
        assert Stage.A in stages and Stage.B in stages, t.id       # both gate stages present
        for c in t.acceptance_criteria:
            if c.stage == Stage.A:
                assert c.check_hint in real_stage_a_checks, (t.id, c.check_hint)


def test_op1_scene_ticket_is_templated_and_routes_to_fast():
    from harness.icarus.agent import ScriptedAgentModel
    from harness.icarus.agent_builder import visual_router
    op1 = {t.id: t for t in one_pond_tickets()}["OP-1"]
    assert "add_plane" in op1.title and "content.gd" in op1.title      # templated
    fast, big = ScriptedAgentModel([]), ScriptedAgentModel([])
    fast.model_id, big.model_id = "fast", "big"
    assert visual_router(fast, big).for_task(op1.title).model_id == "fast"   # -> the fast resident model


def test_one_pond_tickets_are_frozen():
    # freeze() ran in the factory; a frozen ticket exposes its criteria hash for the gatekeeper.
    for t in one_pond_tickets():
        assert getattr(t, "criteria_hash", None), t.id
