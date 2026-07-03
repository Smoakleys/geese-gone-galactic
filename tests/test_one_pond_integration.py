"""Integration: the Icarus-built One Pond modules compose into a working mini game loop.

Not hand-written game logic -- it drives the agent-built game/pond modules end to end, proving the
placement + economy pieces work together over several ticks.
"""

from __future__ import annotations

from game.pond.pond_state import add_building, step


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
