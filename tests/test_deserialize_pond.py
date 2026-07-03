"""Behaviour lock for the Icarus-built pond deserializer (OP-31) + a save/load round-trip."""

from __future__ import annotations

from game.pond.deserialize_pond import deserialize_pond
from game.pond.serialize_pond import serialize_pond


def test_parses_back_to_state():
    assert deserialize_pond("bread=10;bakery@0,0") == {"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}
    assert deserialize_pond("bread=5") == {"bread": 5, "buildings": []}


def test_save_load_round_trip():
    # serialize then deserialize must recover the state exactly (the point of save/load).
    for state in (
        {"bread": 0, "buildings": []},
        {"bread": 42, "buildings": [{"kind": "bakery", "x": 0, "y": 0}, {"kind": "nest", "x": 2, "y": 3}]},
    ):
        assert deserialize_pond(serialize_pond(state)) == state
