"""Behaviour lock for the Icarus-built pond status summary (OP-9, composes predator safety + state)."""

from __future__ import annotations

from game.pond.pond_status import pond_status


def test_safe_when_every_nest_is_near_a_fence():
    state = {"bread": 9, "buildings": [{"kind": "nest", "x": 0, "y": 0},
                                       {"kind": "fence", "x": 1, "y": 0}]}
    assert pond_status(state, 2)["safe"] is True


def test_unsafe_when_a_nest_is_far():
    assert pond_status({"bread": 5, "buildings": [{"kind": "nest", "x": 9, "y": 9}]}, 2)["safe"] is False


def test_bread_passes_through_and_no_nests_is_safe():
    s = pond_status({"bread": 7, "buildings": []}, 2)
    assert s["bread"] == 7 and s["safe"] is True
