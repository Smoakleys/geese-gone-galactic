"""Behaviour lock for the Icarus-built nearest-fence search (OP-19)."""

from __future__ import annotations

from game.pond.nearest_fence import nearest_fence


def test_returns_the_closest_fence():
    assert nearest_fence((0, 0), [(3, 0), (0, 2)]) == (0, 2)      # dist 2 < 3
    assert nearest_fence((5, 5), [(5, 4), (0, 0)]) == (5, 4)      # dist 1


def test_earliest_on_tie_and_none_when_empty():
    assert nearest_fence((0, 0), [(1, 0), (0, 1)]) == (1, 0)      # both dist 1 -> earliest
    assert nearest_fence((0, 0), []) is None
