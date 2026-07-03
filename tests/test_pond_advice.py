"""Behaviour lock for the Icarus-built pond advice/hint system (OP-13)."""

from __future__ import annotations

from game.pond.pond_advice import pond_advice


def test_suggests_a_bakery_first():
    assert pond_advice({"buildings": []}, 2) == "build a bakery"


def test_then_a_well_for_a_dry_bakery():
    assert pond_advice({"buildings": [{"kind": "bakery", "x": 0, "y": 0}]}, 2) == "build a well"


def test_then_a_fence_for_an_exposed_nest():
    b = [{"kind": "bakery", "x": 0, "y": 0}, {"kind": "well", "x": 1, "y": 0}, {"kind": "nest", "x": 5, "y": 5}]
    assert pond_advice({"buildings": b}, 2) == "build a fence"


def test_looking_good_when_all_covered():
    b = [{"kind": "bakery", "x": 0, "y": 0}, {"kind": "well", "x": 1, "y": 0}]
    assert pond_advice({"buildings": b}, 2) == "looking good"
