"""Behaviour lock for the Icarus-built build-cost rule (OP-15): buildings cost bread to place."""

from __future__ import annotations

from game.pond.build_cost import total_cost


def test_sums_per_kind_costs():
    assert total_cost([{"kind": "bakery"}, {"kind": "nest"}]) == 6      # 5 + 1
    assert total_cost([{"kind": "well"}, {"kind": "well"}]) == 6        # 3 + 3


def test_empty_and_unknown_cost_nothing():
    assert total_cost([]) == 0
    assert total_cost([{"kind": "rocket"}]) == 0                        # unknown kind -> 0
