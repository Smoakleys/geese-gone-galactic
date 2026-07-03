"""Behaviour lock for the Icarus-built water-access rule (OP-11): bakeries need a well nearby."""

from __future__ import annotations

from game.pond.water_access import has_water


def test_bakery_near_a_well_has_water():
    assert has_water([{"kind": "bakery", "x": 0, "y": 0}, {"kind": "well", "x": 1, "y": 0}], 2) is True


def test_bakery_far_from_every_well_lacks_water():
    assert has_water([{"kind": "bakery", "x": 9, "y": 9}, {"kind": "well", "x": 0, "y": 0}], 2) is False


def test_no_bakeries_counts_as_watered():
    assert has_water([], 2) is True
    assert has_water([{"kind": "well", "x": 0, "y": 0}], 2) is True
