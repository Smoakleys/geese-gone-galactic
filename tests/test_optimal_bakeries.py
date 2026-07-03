"""Behaviour lock for the Icarus-built production planner (OP-32)."""

from __future__ import annotations

from game.pond.optimal_bakeries import optimal_bakeries


def test_ceil_division_of_target():
    assert optimal_bakeries(10, 0) == 4     # each makes 3 -> ceil(10/3)
    assert optimal_bakeries(9, 0) == 3      # exact
    assert optimal_bakeries(8, 1) == 2      # each makes 4 -> ceil(8/4)


def test_non_positive_target():
    assert optimal_bakeries(0, 0) == 0
    assert optimal_bakeries(-5, 2) == 0
