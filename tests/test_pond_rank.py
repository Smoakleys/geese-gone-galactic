"""Behaviour lock for the Icarus-built pond rank/progression (OP-16)."""

from __future__ import annotations

from game.pond.pond_rank import pond_rank


def test_ranks_by_score():
    assert pond_rank(0) == "hamlet"
    assert pond_rank(19) == "hamlet"
    assert pond_rank(30) == "village"
    assert pond_rank(75) == "town"
    assert pond_rank(250) == "city"


def test_boundaries_go_to_the_higher_tier():
    assert pond_rank(20) == "village"
    assert pond_rank(50) == "town"
    assert pond_rank(100) == "city"
