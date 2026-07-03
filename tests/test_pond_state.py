"""Behaviour lock for the Icarus-built One Pond simulation (OP-4)."""

from __future__ import annotations

from game.pond.pond_state import add_building, step


def test_step_ticks_bread_by_building_counts():
    state = {"bread": 5, "buildings": [{"kind": "bakery", "x": 0, "y": 0},
                                       {"kind": "nest", "x": 1, "y": 1}]}
    assert step(state)["bread"] == 7                       # 5 + 3 (bakery) - 1 (nest)


def test_step_clamps_bread_at_zero():
    state = {"bread": 0, "buildings": [{"kind": "nest", "x": 0, "y": 0}]}
    assert step(state)["bread"] == 0                       # never negative


def test_add_building_validates_bounds_and_occupancy():
    s = add_building({"bread": 0, "buildings": []}, "bakery", 1, 1, 4)
    assert len(s["buildings"]) == 1                        # in-bounds -> added
    s = add_building(s, "nest", 9, 9, 4)
    assert len(s["buildings"]) == 1                        # out-of-bounds -> unchanged
    s = add_building(s, "nest", 1, 1, 4)
    assert len(s["buildings"]) == 1                        # occupied cell -> unchanged
