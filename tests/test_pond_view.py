"""The logic->visual bridge packaged: an actual played pond STATE renders to a lit 3D village scene."""

from __future__ import annotations

import re

import pytest

from game.godot.binary import godot_path
from game.godot.checks import GodotParseCheck, GodotRenderCheck
from game.godot import models as M
from game.godot.pond_view import pond_state_to_scene_gd, render_pond_state
from game.pond import add_building, step
from harness.models import Result, Ticket, TicketKind

_GOOSE_BEAK = "_cone(0.2, 0.66)"        # unique to a goose (its orange beak) -> counts geese in a scene


def _played_state() -> dict:
    state = {"bread": 20, "buildings": []}
    state = add_building(state, "bakery", 1, 1, 8)
    state = add_building(state, "granary", 2, 1, 8)
    state = add_building(state, "nest", 4, 3, 8)
    state = add_building(state, "well", 0, 4, 8)
    return step(state)


def _build_body(gd: str) -> str:
    return gd[gd.index("func build"):]


def test_state_renders_land_pond_modelled_buildings_and_geese():
    state = _played_state()                      # bakery, granary, nest, well -> 1 nest
    nests = sum(1 for b in state["buildings"] if b["kind"] == "nest")
    gd = pond_state_to_scene_gd(state)
    assert "func build" in gd
    body = _build_body(gd)
    assert M.GRASS in gd and M.POND in gd        # grass + pond
    assert body.count("PlaneMesh.new()") == 2
    assert body.count(_GOOSE_BEAK) == nests      # one goose per nest
    assert "_prism(" in body                      # modelled buildings (a gabled roof), not plain boxes
    assert "DirectionalLight3D" in gd            # lit


def test_geese_only_appear_for_nests():
    no_nest = {"bread": 0, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}
    assert _GOOSE_BEAK not in pond_state_to_scene_gd(no_nest)
    two = {"bread": 0, "buildings": [{"kind": "nest", "x": 1, "y": 1}, {"kind": "nest", "x": 4, "y": 2}]}
    assert pond_state_to_scene_gd(two).count(_GOOSE_BEAK) == 2


def test_empty_pond_still_composes_land_and_water():
    body = _build_body(pond_state_to_scene_gd({"bread": 0, "buildings": []}))
    assert body.count("PlaneMesh.new()") == 2 and _GOOSE_BEAK not in body


def test_high_coord_state_is_centered_not_off_land():
    # grid x -> world x*_SPACING (high coords reach world ~21); the fixed camera frames the origin, so a
    # played state with high-coord props MUST be footprint-centered or it floats off the land (real bug).
    state = {"bread": 0, "buildings": [{"kind": "bakery", "x": 7, "y": 7}, {"kind": "nest", "x": 6, "y": 5}]}
    body = _build_body(pond_state_to_scene_gd(state))
    xs = [abs(float(v)) for v in re.findall(r"Vector3\(([-\d.]+),", body)]
    assert xs
    assert max(xs) <= 12, f"a part sits off-frame (not centered): max |x| = {max(xs)}"


@pytest.mark.skipif(godot_path() is None, reason="Godot binary not installed")
def test_played_state_renders_through_the_gate(tmp_path):
    state = _played_state()
    ok, detail = render_pond_state(state, tmp_path / "out.png")
    assert ok, detail
    (tmp_path / "scene.gd").write_text(pond_state_to_scene_gd(state))
    t = Ticket(id="t", title="t", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    assert GodotParseCheck().run(tmp_path, t).result == Result.PASS
    assert GodotRenderCheck().run(tmp_path, t).result == Result.PASS
