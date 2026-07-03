"""Behaviour lock for the Icarus-built building inventory (OP-20)."""

from __future__ import annotations

from game.pond.count_by_kind import count_by_kind


def test_counts_each_kind():
    assert count_by_kind([{"kind": "bakery"}, {"kind": "bakery"}, {"kind": "nest"}]) == {"bakery": 2, "nest": 1}
    assert count_by_kind([{"kind": "well"}]) == {"well": 1}


def test_empty_is_empty_dict():
    assert count_by_kind([]) == {}
