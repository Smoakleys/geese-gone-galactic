"""The logic->visual bridge packaged: an actual played pond STATE renders to a lit 3D scene."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from game.godot.binary import godot_path
from game.godot.checks import GodotParseCheck, GodotRenderCheck
from game.godot.pond_view import pond_state_to_scene_gd, render_pond_state
from game.pond import add_building, step
from harness.models import Result, Ticket, TicketKind


def _played_state() -> dict:
    state = {"bread": 20, "buildings": []}
    state = add_building(state, "bakery", 1, 1, 8)
    state = add_building(state, "granary", 2, 1, 8)
    state = add_building(state, "nest", 4, 3, 8)
    state = add_building(state, "well", 0, 4, 8)
    return step(state)


def _build_body(gd: str) -> str:
    # the composed scene is camera + helper DEFINITIONS + the build() call body; count calls in build()
    return gd[gd.index("func build"):]


def test_state_to_scene_gd_has_land_pond_buildings_and_geese():
    state = _played_state()                      # bakery, granary, nest, well -> 4 buildings, 1 nest
    nests = sum(1 for b in state["buildings"] if b["kind"] == "nest")
    gd = pond_state_to_scene_gd(state)
    assert "func build" in gd
    body = _build_body(gd)
    assert body.count("add_plane(") == 2         # land + pond
    assert body.count("add_box(") == 4 + nests   # 4 building boxes + 1 goose beak per nest
    assert body.count("add_sphere(root, 0.35") == nests   # one goose body per nest
    assert "DirectionalLight3D" in gd            # composed through the LIT template


def test_geese_only_appear_for_nests():
    # a pond with no nests draws no geese; each nest adds exactly one goose.
    no_nest = {"bread": 0, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}
    assert "add_sphere(root, 0.35" not in pond_state_to_scene_gd(no_nest)
    two_nests = {"bread": 0, "buildings": [{"kind": "nest", "x": 1, "y": 1}, {"kind": "nest", "x": 4, "y": 2}]}
    assert pond_state_to_scene_gd(two_nests).count("add_sphere(root, 0.35") == 2


def test_empty_pond_still_composes_land_and_water():
    body = _build_body(pond_state_to_scene_gd({"bread": 0, "buildings": []}))
    assert body.count("add_plane(") == 2 and body.count("add_box(") == 0


@pytest.mark.skipif(godot_path() is None, reason="Godot binary not installed")
def test_played_state_renders_through_the_gate(tmp_path):
    state = _played_state()
    ok, detail = render_pond_state(state, tmp_path / "out.png")
    assert ok, detail
    (tmp_path / "scene.gd").write_text(pond_state_to_scene_gd(state))
    t = Ticket(id="t", title="t", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    assert GodotParseCheck().run(tmp_path, t).result == Result.PASS
    assert GodotRenderCheck().run(tmp_path, t).result == Result.PASS
