"""Behaviour lock for the Icarus-built One Pond logic modules (OP-2 bread tick, OP-3 placement)."""

from __future__ import annotations

from game.pond.bread_tick import tick
from game.pond.placement import is_valid


def test_bread_tick_adds_bakery_subtracts_goose_without_mutating():
    state = {"bakery_bread": 5, "goose_bread": 3}
    out = tick(state)
    assert out == {"bakery_bread": 6, "goose_bread": 2}
    assert state == {"bakery_bread": 5, "goose_bread": 3}   # original untouched


def test_bread_tick_clamps_goose_at_zero_and_defaults_missing_keys():
    assert tick({"goose_bread": 0}) == {"bakery_bread": 1, "goose_bread": 0}
    assert tick({}) == {"bakery_bread": 1, "goose_bread": 0}


def test_placement_valid_and_invalid_layouts():
    assert is_valid([(0, 0), (1, 1), (3, 2)], 4) is True
    assert is_valid([(0, 0), (5, 0)], 4) is False       # out of bounds
    assert is_valid([(1, 1), (1, 1)], 4) is False       # overlap
    assert is_valid([], 4) is True                       # empty layout is valid
