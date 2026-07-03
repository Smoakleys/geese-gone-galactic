"""Behaviour lock for the Icarus-built pond outcome evaluation (OP-10)."""

from __future__ import annotations

from game.pond.pond_outcome import pond_outcome


def test_lost_when_no_bread():
    assert pond_outcome({"bread": 0, "buildings": []}, 2) == "lost"
    assert pond_outcome({"bread": -1, "buildings": []}, 2) == "lost"


def test_dry_when_a_bakery_lacks_a_well():
    # water access is checked after bread and before safety
    assert pond_outcome({"bread": 5, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}, 2) == "dry"


def test_unsafe_when_a_nest_is_unprotected():
    assert pond_outcome({"bread": 5, "buildings": [{"kind": "nest", "x": 9, "y": 9}]}, 2) == "unsafe"


def test_thriving_when_solvent_and_safe():
    safe = {"bread": 5, "buildings": [{"kind": "nest", "x": 0, "y": 0}, {"kind": "fence", "x": 1, "y": 0}]}
    assert pond_outcome(safe, 2) == "thriving"
    assert pond_outcome({"bread": 3, "buildings": []}, 2) == "thriving"   # no nests -> safe
