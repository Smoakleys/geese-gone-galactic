"""Behaviour lock for the Icarus-built composed economy (OP-8, uses the granary synergy)."""

from __future__ import annotations

from game.pond.pond_economy import tick_bread


def _b(*kinds):
    return [{"kind": k} for k in kinds]


def test_granary_synergy_in_the_tick():
    assert tick_bread(_b("bakery", "bakery", "granary", "nest")) == 7   # 2*(3+1) - 1
    assert tick_bread(_b("bakery", "granary", "granary", "granary")) == 6  # 1*(3+3)


def test_base_and_nests():
    assert tick_bread(_b("bakery", "bakery", "bakery", "bakery")) == 12  # 4*3
    assert tick_bread(_b("bakery", "nest", "nest")) == 1                 # 3 - 2 (may go negative elsewhere)


def test_empty_and_kind_strings():
    assert tick_bread([]) == 0
    assert tick_bread(_b("granary", "granary")) == 0    # no bakery -> no bread
