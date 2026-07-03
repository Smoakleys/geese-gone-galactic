"""Integration: the Icarus-built One Pond modules compose into a working mini game loop.

Not hand-written game logic -- it drives the agent-built game/pond modules end to end, proving the
placement + economy pieces work together over several ticks.
"""

from __future__ import annotations

import pytest

from game.godot.binary import godot_path
from game.pond.pond_state import add_building, step
from game.pond.predator import is_safe


def test_one_pond_mini_playthrough():
    state = {"bread": 10, "buildings": []}
    # place two bakeries and a nest on an 8x8 grid
    state = add_building(state, "bakery", 0, 0, 8)
    state = add_building(state, "bakery", 1, 0, 8)
    state = add_building(state, "nest", 2, 0, 8)
    assert len(state["buildings"]) == 3

    # a rejected placement (occupied) must not change the layout
    state = add_building(state, "nest", 0, 0, 8)
    assert len(state["buildings"]) == 3

    # 2 bakeries (+6) - 1 nest (-1) = +5 bread per tick; run 3 ticks
    for _ in range(3):
        state = step(state)
    assert state["bread"] == 25          # 10 + 3 * 5


def test_one_pond_nests_can_starve_but_not_go_negative():
    state = {"bread": 2, "buildings": [{"kind": "nest", "x": 0, "y": 0}]}
    for _ in range(5):
        state = step(state)
    assert state["bread"] == 0           # -1/tick, clamped at 0 (never negative)


def _nests_and_fences(state):
    nests = [(b["x"], b["y"]) for b in state["buildings"] if b["kind"] == "nest"]
    fences = [(b["x"], b["y"]) for b in state["buildings"] if b["kind"] == "fence"]
    return nests, fences


def test_pond_placements_feed_predator_safety():
    # place a nest next to a fence -> safe; a second nest far from any fence -> the pond is unsafe
    state = {"bread": 0, "buildings": []}
    state = add_building(state, "nest", 2, 2, 8)
    state = add_building(state, "fence", 3, 2, 8)     # Manhattan distance 1 from the nest
    nests, fences = _nests_and_fences(state)
    assert is_safe(nests, fences, 2) is True

    state = add_building(state, "nest", 7, 7, 8)       # far from the only fence
    nests, fences = _nests_and_fences(state)
    assert is_safe(nests, fences, 2) is False


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_pond_state_renders_to_a_scene():
    # the full logic->visual bridge, all Icarus-built: state -> build_body -> template -> rendered scene
    from game.godot.capture import color_fraction, green_dominance, render_gdscript, significant_colors
    from game.godot.scene_template import compose_scene
    from game.pond.pond_scene import build_body

    state = {"bread": 0, "buildings": []}
    state = add_building(state, "bakery", 0, 0, 8)
    state = add_building(state, "nest", 2, 1, 8)
    state = add_building(state, "fence", 3, 1, 8)

    content = ("func build(root: Node3D) -> void:\n"
               "\tadd_plane(root, Vector2(16, 16), Color.GREEN)\n"
               "\tadd_plane(root, Vector2(6, 6), Color.BLUE, 0.1)\n"
               + "\n".join("\t" + ln for ln in build_body(state["buildings"]).splitlines()))
    scene = compose_scene(content)

    import tempfile
    from pathlib import Path
    d = Path(tempfile.mkdtemp())
    gd = d / "scene.gd"
    gd.write_text(scene)
    out = d / "render.png"
    ok, detail = render_gdscript(gd, out)
    assert ok, detail
    assert green_dominance(out) >= 15                       # land visible
    assert color_fraction(out, "blue") >= 0.04              # pond visible
    assert significant_colors(out) >= 3                     # land + water + building(s)
