"""Behaviour lock for the Icarus-built pond net-worth score (OP-12)."""

from __future__ import annotations

from game.pond.pond_score import pond_score


def test_bread_only():
    assert pond_score({"bread": 5, "buildings": []}) == 5


def test_weighted_building_values():
    assert pond_score({"bread": 0, "buildings": [{"kind": "bakery"}]}) == 10
    assert pond_score({"bread": 1, "buildings": [{"kind": "well"}]}) == 3   # other kind -> 2


def test_mixed_pond():
    s = {"bread": 10, "buildings": [{"kind": "bakery"}, {"kind": "granary"}, {"kind": "nest"}]}
    assert pond_score(s) == 28   # 10 + 10 + 5 + 3
