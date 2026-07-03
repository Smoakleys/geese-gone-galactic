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


def test_state_to_scene_gd_has_land_pond_and_a_box_per_building():
    gd = pond_state_to_scene_gd(_played_state())
    assert "func build" in gd and "add_plane" in gd
    assert gd.count("add_box") == 4          # one per placed building
    assert "DirectionalLight3D" in gd        # composed through the LIT template


def test_empty_pond_still_composes_land_and_water():
    gd = pond_state_to_scene_gd({"bread": 0, "buildings": []})
    assert gd.count("add_plane") == 2 and gd.count("add_box") == 0


@pytest.mark.skipif(godot_path() is None, reason="Godot binary not installed")
def test_played_state_renders_through_the_gate(tmp_path):
    state = _played_state()
    ok, detail = render_pond_state(state, tmp_path / "out.png")
    assert ok, detail
    (tmp_path / "scene.gd").write_text(pond_state_to_scene_gd(state))
    t = Ticket(id="t", title="t", kind=TicketKind.SYSTEM, acceptance_criteria=[])
    assert GodotParseCheck().run(tmp_path, t).result == Result.PASS
    assert GodotRenderCheck().run(tmp_path, t).result == Result.PASS
