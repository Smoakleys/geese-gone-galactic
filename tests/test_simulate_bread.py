"""Behaviour lock for the Icarus-built bread projection (OP-22) -- iterative with per-tick clamping."""

from __future__ import annotations

from game.pond.simulate_bread import simulate_bread


def test_projects_over_ticks():
    assert simulate_bread(10, 2, 1, 3) == 25       # 10 + 3*(6-1)
    assert simulate_bread(5, 1, 0, 2) == 11        # 5 + 2*3


def test_clamps_each_tick():
    # a formula (2 - 5) would give -3; clamping each tick keeps it at 0
    assert simulate_bread(2, 0, 1, 5) == 0
