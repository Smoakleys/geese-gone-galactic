"""The One Pond game core exposes a clean composed public API."""

from __future__ import annotations

import game.pond as pond


def test_public_api_is_exported_and_callable():
    for name in ("tick", "step", "add_building", "is_valid", "is_safe",
                 "production", "tick_bread", "build_body", "pond_status", "pond_outcome"):
        assert hasattr(pond, name), name

    # a tiny composed smoke run through the package API
    state = {"bread": 5, "buildings": []}
    state = pond.add_building(state, "bakery", 0, 0, 8)
    state = pond.step(state)                       # +3 bread
    assert state["bread"] == 8
    assert pond.pond_outcome(state, 2) == "thriving"
