"""Behaviour lock for the Icarus-built affordability filter (OP-27)."""

from __future__ import annotations

from game.pond.affordable_buildings import affordable_buildings


def test_sorted_affordable_kinds():
    assert affordable_buildings(4) == ["fence", "granary", "nest", "well"]   # all but bakery (5)
    assert affordable_buildings(5) == ["bakery", "fence", "granary", "nest", "well"]


def test_low_and_zero_bread():
    assert affordable_buildings(1) == ["nest"]
    assert affordable_buildings(0) == []


def test_boundaries_and_negative():
    # cost is inclusive (<=): a building priced exactly at `bread` is affordable; negative -> nothing.
    assert affordable_buildings(2) == ["fence", "nest"]          # fence costs exactly 2
    assert affordable_buildings(3) == ["fence", "nest", "well"]  # well costs exactly 3
    assert affordable_buildings(-1) == []
