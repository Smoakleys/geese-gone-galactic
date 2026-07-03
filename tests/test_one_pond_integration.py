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


def test_full_game_plays_to_a_thriving_outcome():
    from game.pond.pond_outcome import pond_outcome
    state = {"bread": 5, "buildings": []}
    state = add_building(state, "bakery", 0, 0, 8)
    state = add_building(state, "well", 1, 0, 8)          # water for the bakery (else 'dry')
    state = add_building(state, "nest", 3, 3, 8)
    state = add_building(state, "fence", 3, 4, 8)        # protect the nest
    for _ in range(3):
        state = step(state)                              # +3 bakery - 1 nest = +2/tick
    assert state["bread"] == 11
    assert pond_outcome(state, 2) == "thriving"          # solvent, watered, AND safe


def test_full_game_can_be_lost_by_starvation():
    from game.pond.pond_outcome import pond_outcome
    state = {"bread": 2, "buildings": [{"kind": "nest", "x": 0, "y": 0}]}   # a goose, no bakery
    for _ in range(5):
        state = step(state)                              # -1/tick, clamped at 0
    assert state["bread"] == 0
    assert pond_outcome(state, 2) == "lost"              # bread gone -> lost (checked before safety)


def test_full_one_pond_playthrough_with_synergy_and_status():
    # all the composed mechanics as one game: place -> tick (granary synergy) -> status (predator safety)
    from game.pond.pond_status import pond_status
    state = {"bread": 5, "buildings": []}
    state = add_building(state, "bakery", 0, 0, 8)
    state = add_building(state, "granary", 1, 0, 8)     # boosts every bakery
    state = add_building(state, "nest", 5, 5, 8)
    state = add_building(state, "fence", 5, 6, 8)        # protects the nest
    assert len(state["buildings"]) == 4

    state = step(state)                                  # 1 bakery * (3 + 1 granary) - 1 nest = +3
    assert state["bread"] == 8

    status = pond_status(state, 2)
    assert status["bread"] == 8
    assert status["safe"] is True                        # the nest is within reach of the fence

    # move the fence away (rebuild the layout without it near the nest) -> unsafe
    far = {"bread": 8, "buildings": [{"kind": "nest", "x": 5, "y": 5}, {"kind": "fence", "x": 0, "y": 0}]}
    assert pond_status(far, 2)["safe"] is False


def test_a_well_built_pond_is_watered_safe_and_thriving():
    # exercises ALL the composed mechanics: placement + water + synergy economy + predator + status + outcome
    from game.pond.water_access import has_water
    from game.pond.pond_status import pond_status
    from game.pond.pond_outcome import pond_outcome
    state = {"bread": 5, "buildings": []}
    state = add_building(state, "bakery", 0, 0, 8)
    state = add_building(state, "well", 1, 0, 8)          # water for the bakery
    state = add_building(state, "granary", 0, 1, 8)        # boosts the bakery
    state = add_building(state, "nest", 4, 4, 8)
    state = add_building(state, "fence", 4, 5, 8)          # protect the nest
    assert has_water(state["buildings"], 2) is True

    for _ in range(3):
        state = step(state)                                # 1 bakery * (3 + 1 granary) - 1 nest = +3/tick
    assert state["bread"] == 14

    assert pond_status(state, 2)["safe"] is True
    assert pond_outcome(state, 2) == "thriving"


def test_a_bakery_without_a_well_is_not_watered():
    from game.pond.water_access import has_water
    assert has_water([{"kind": "bakery", "x": 0, "y": 0}], 2) is False


def test_advice_guides_a_pond_to_thriving():
    # follow pond_advice step by step; it should walk an empty pond to a thriving one.
    from game.pond.pond_advice import pond_advice
    from game.pond.pond_outcome import pond_outcome
    state = {"bread": 20, "buildings": []}

    assert pond_advice(state, 2) == "build a bakery"
    state = add_building(state, "bakery", 0, 0, 8)

    assert pond_advice(state, 2) == "build a well"          # bakery now needs water
    state = add_building(state, "well", 1, 0, 8)

    assert pond_advice(state, 2) == "looking good"          # no nests -> nothing exposed
    state = step(state)
    assert pond_outcome(state, 2) == "thriving"             # the guided pond thrives


def test_predators_drain_an_unsafe_pond_over_time():
    # predator_loss gives predator-safety a real economic bite: two identical bakery+nest ponds, one fenced.
    from game.pond.predator_loss import predator_loss
    safe = {"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0},
                                       {"kind": "nest", "x": 2, "y": 2}, {"kind": "fence", "x": 3, "y": 2}]}
    unsafe = {"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0},
                                         {"kind": "nest", "x": 2, "y": 2}]}
    for _ in range(3):
        safe = step(safe)
        safe["bread"] = max(safe["bread"] - predator_loss(safe, 2), 0)
        unsafe = step(unsafe)
        unsafe["bread"] = max(unsafe["bread"] - predator_loss(unsafe, 2), 0)
    assert safe["bread"] == 16          # +2/tick, no predator loss
    assert unsafe["bread"] == 10        # +2/tick economy, -2/tick predators -> flat
    assert unsafe["bread"] < safe["bread"]


def test_the_whole_game_composes_over_a_realistic_playthrough():
    # every mechanic together: placement + water + synergy economy + predators + status + outcome + score + advice
    from game.pond import (pond_advice, pond_outcome, pond_score, pond_status, predator_loss, has_water)
    state = {"bread": 15, "buildings": []}
    for kind, x, y in [("bakery", 0, 0), ("well", 1, 0), ("granary", 0, 1), ("nest", 4, 4), ("fence", 4, 5)]:
        state = add_building(state, kind, x, y, 8)
    assert has_water(state["buildings"], 2)                  # the bakery is watered
    assert pond_advice(state, 2) == "looking good"           # nothing left to fix

    for _ in range(4):
        state = step(state)                                  # 1 bakery*(3+1 granary) - 1 nest = +3/tick
        state["bread"] = max(state["bread"] - predator_loss(state, 2), 0)   # fenced nest -> no loss

    assert state["bread"] == 27                              # 15 + 4*3, predators took nothing
    assert pond_status(state, 2)["safe"] is True
    assert pond_outcome(state, 2) == "thriving"
    assert pond_score(state) == 49                           # 27 bread + 10+5+3+2+2 buildings


def test_all_modules_handle_the_empty_pond_gracefully():
    # the degenerate state (no bread, no buildings) must not crash any module and must read consistently.
    from game.pond import (pond_outcome, pond_status, pond_score, pond_advice, has_water,
                           predator_loss, total_cost)
    empty = {"bread": 0, "buildings": []}
    assert pond_outcome(empty, 2) == "lost"                 # no bread
    assert pond_status(empty, 2) == {"bread": 0, "safe": True}
    assert pond_score(empty) == 0
    assert pond_advice(empty, 2) == "build a bakery"        # start here
    assert has_water([], 2) is True                         # no bakeries -> watered
    assert predator_loss(empty, 2) == 0
    assert total_cost([]) == 0
    assert step(empty)["bread"] == 0                        # nothing produced, clamps at 0


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
