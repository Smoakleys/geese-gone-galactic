"""Behaviour lock for the Icarus-built granary synergy (OP-7)."""

from __future__ import annotations

from game.pond.granary import production


def test_granary_boosts_every_bakery():
    assert production(2, 1) == 8        # 2 * (3 + 1)
    assert production(3, 2) == 15       # 3 * (3 + 2)


def test_base_output_with_no_granaries():
    assert production(4, 0) == 12       # 4 * 3


def test_no_bakeries_means_no_bread():
    assert production(0, 5) == 0        # granaries do nothing without a bakery
