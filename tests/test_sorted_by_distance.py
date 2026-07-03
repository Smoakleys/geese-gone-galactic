"""Behaviour lock for the Icarus-built distance sort (OP-21)."""

from __future__ import annotations

from game.pond.sorted_by_distance import sorted_by_distance


def test_sorts_ascending_by_distance():
    assert sorted_by_distance([(5, 5), (1, 0), (0, 2)], (0, 0)) == [(1, 0), (0, 2), (5, 5)]


def test_stable_on_ties_and_empty():
    assert sorted_by_distance([(0, 1), (1, 0)], (0, 0)) == [(0, 1), (1, 0)]      # both dist 1 -> stable
    assert sorted_by_distance([], (0, 0)) == []
