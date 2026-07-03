"""Behaviour lock for the Icarus-built One Pond predator-safety rule (OP-5)."""

from __future__ import annotations

from game.pond.predator import is_safe


def test_all_nests_within_reach_of_a_fence_are_safe():
    assert is_safe([(0, 0), (1, 0)], [(0, 0)], 2) is True     # both within Manhattan 2 of the fence


def test_a_nest_out_of_reach_is_unsafe():
    assert is_safe([(9, 9)], [(0, 0)], 2) is False            # far from the only fence


def test_edge_cases():
    assert is_safe([], [(0, 0)], 2) is True                   # no nests -> safe
    assert is_safe([(0, 0)], [], 2) is False                  # nests but no fences -> unsafe
