"""Behaviour lock for the Icarus-built state->scene bridge (OP-6)."""

from __future__ import annotations

from game.pond.pond_scene import build_body


def test_build_body_one_add_box_line_per_building():
    body = build_body([{"kind": "bakery", "x": 0, "y": 0}, {"kind": "nest", "x": 2, "y": 1}])
    # REAL newlines (chr 10) so each add_box is its own GDScript statement -- not a literal backslash-n
    lines = [ln for ln in body.split(chr(10)) if "add_box" in ln]
    assert len(lines) == 2                                   # one statement per building, newline-separated


def test_build_body_colours_and_positions():
    body = build_body([{"kind": "bakery", "x": 3, "y": 1},
                       {"kind": "nest", "x": 0, "y": 0},
                       {"kind": "fence", "x": 1, "y": 2}])
    assert "0.5, 0.3, 0.1" in body      # bakery brown
    assert "0.8, 0.7, 0.4" in body      # nest tan
    assert "0.5, 0.5, 0.5" in body      # fence grey
    assert "3 * 2" in body and "1 * 2" in body    # grid position scaled


def test_build_body_empty_is_empty():
    assert build_body([]).strip() == ""
