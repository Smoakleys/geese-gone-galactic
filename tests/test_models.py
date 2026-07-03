"""The reusable low-poly model library (game/godot/models.py) -- geese + pond buildings as GDScript."""

from __future__ import annotations

from pathlib import Path

import pytest

from game.godot import models as M
from game.godot.binary import godot_path


def test_building_lines_cover_every_pond_kind():
    for kind in ("bakery", "granary", "nest", "well", "fence"):
        lines = M.building_lines(kind, (0, 0, 0))
        assert lines, kind
        assert all("_part(root" in ln for ln in lines), kind          # every line draws a modelled part
        assert all(not ln.startswith("\t") for ln in lines)           # spaces, never tabs (mixed = parse err)


def test_unknown_building_kind_falls_back_to_a_hut():
    lines = M.building_lines("mystery-hall", (1, 0, 2))
    assert lines and any("_prism" in ln for ln in lines)              # still a roofed prop, not a crash


def test_goose_has_beak_eyes_and_enough_parts():
    lines = M.goose_lines((0, 0, 0))
    body = "\n".join(lines)
    assert M._BEAK in body                                            # orange beak
    assert M._DARK in body                                            # a dark eye
    assert body.count("_ball(") >= 10                                 # body + neck + head + eyes
    # facing flips the model across X so a goose can look either way
    left = "\n".join(M.goose_lines((0, 0, 0), face=-1))
    right = "\n".join(M.goose_lines((0, 0, 0), face=1))
    assert left != right


def test_compose_model_scene_is_wellformed_and_space_indented():
    scene = M.compose_model_scene(M.bakery_lines((0, 0, 0)))
    assert "func _ready" in scene and "func build" in scene
    assert "_prism" in scene and "_cone" in scene                     # rich helpers present
    assert "\t" not in scene                                          # no tabs anywhere


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_a_model_scene_actually_renders(tmp_path):
    from game.godot.capture import render_gdscript, significant_colors, color_fraction
    body = ["    var g := PlaneMesh.new()", "    g.size = Vector2(12, 12)",
            f"    _part(root, g, {M.GRASS}, Vector3(0, 0, 0))"]
    body += M.bakery_lines((-1.5, 0, 0)) + M.nest_lines((1.6, 0, 0.6)) + M.goose_lines((0.2, 0, -1.4), s=0.7)
    scene = M.compose_model_scene(body, cam_target=(0, 0.8, 0), cam_size=7)   # tight, props prominent
    gd = tmp_path / "scene.gd"
    gd.write_text(scene, encoding="utf-8")
    ok, detail = render_gdscript(gd, tmp_path / "out.png")
    assert ok, detail
    assert color_fraction(tmp_path / "out.png", "green") >= 0.08      # land visible
    assert significant_colors(tmp_path / "out.png") >= 3              # land + roof/wall + goose etc.
