"""Behaviour lock for the Icarus-built predator-loss rule (OP-14): predators eat bread from unguarded nests."""

from __future__ import annotations

from game.pond.predator_loss import predator_loss


def test_unguarded_nest_loses_bread():
    assert predator_loss({"buildings": [{"kind": "nest", "x": 0, "y": 0}]}, 2) == 2


def test_guarded_nest_loses_nothing():
    b = [{"kind": "nest", "x": 0, "y": 0}, {"kind": "fence", "x": 1, "y": 0}]
    assert predator_loss({"buildings": b}, 2) == 0


def test_only_unguarded_nests_count():
    b = [{"kind": "nest", "x": 0, "y": 0}, {"kind": "nest", "x": 9, "y": 9}, {"kind": "fence", "x": 1, "y": 0}]
    assert predator_loss({"buildings": b}, 2) == 2       # one guarded, one exposed
    assert predator_loss({"buildings": []}, 2) == 0
