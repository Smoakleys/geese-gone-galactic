"""Behaviour lock for the Icarus-built pond serializer (OP-30) -- exact string format."""

from __future__ import annotations

from game.pond.serialize_pond import serialize_pond


def test_exact_format():
    assert serialize_pond({"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}) == "bread=10;bakery@0,0"
    assert serialize_pond({"bread": 5, "buildings": []}) == "bread=5"


def test_multiple_buildings_in_order():
    s = {"bread": 0, "buildings": [{"kind": "nest", "x": 2, "y": 3}, {"kind": "well", "x": 1, "y": 0}]}
    assert serialize_pond(s) == "bread=0;nest@2,3;well@1,0"
