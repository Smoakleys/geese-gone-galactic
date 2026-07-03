"""Behaviour lock for the Icarus-built goose population (OP-17): the pond's inhabitants."""

from __future__ import annotations

from game.pond.goose_count import goose_count


def test_four_geese_per_nest():
    assert goose_count([{"kind": "nest"}, {"kind": "nest"}]) == 8
    assert goose_count([{"kind": "nest"}, {"kind": "bakery"}]) == 4


def test_no_nests_no_geese():
    assert goose_count([]) == 0
    assert goose_count([{"kind": "bakery"}, {"kind": "well"}]) == 0
