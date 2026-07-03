"""The authored One Pond ticket backlog is well-formed and references real certified gates."""

from __future__ import annotations

from game.onepond_tickets import one_pond_tickets
from harness.models import Stage


def test_one_pond_tickets_well_formed_and_reference_real_gates():
    tickets = one_pond_tickets()
    assert [t.id for t in tickets] == ["OP-1", "OP-2", "OP-3"]
    # Stage-A hints must name checks that actually exist and are certified elsewhere in the suite.
    real_stage_a_checks = {"godot_parse", "godot_render", "python_syntax", "json_valid"}
    for t in tickets:
        stages = {c.stage for c in t.acceptance_criteria}
        assert Stage.A in stages and Stage.B in stages, t.id       # both gate stages present
        for c in t.acceptance_criteria:
            if c.stage == Stage.A:
                assert c.check_hint in real_stage_a_checks, (t.id, c.check_hint)


def test_one_pond_tickets_are_frozen():
    # freeze() ran in the factory; a frozen ticket exposes its criteria hash for the gatekeeper.
    for t in one_pond_tickets():
        assert getattr(t, "criteria_hash", None), t.id
