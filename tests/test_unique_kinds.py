"""Behaviour lock for the Icarus-built distinct-kinds list (OP-23)."""

from __future__ import annotations

from game.pond.unique_kinds import unique_kinds


def test_distinct_sorted_kinds():
    assert unique_kinds([{"kind": "nest"}, {"kind": "bakery"}, {"kind": "nest"}]) == ["bakery", "nest"]
    assert unique_kinds([{"kind": "well"}, {"kind": "well"}]) == ["well"]


def test_empty():
    assert unique_kinds([]) == []
