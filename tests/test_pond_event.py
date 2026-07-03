"""Behaviour lock for the Icarus-built pond events (OP-28)."""

from __future__ import annotations

from game.pond.pond_event import apply_event


def test_events_change_bread():
    assert apply_event({"bread": 10, "buildings": []}, "harvest")["bread"] == 20
    assert apply_event({"bread": 11, "buildings": []}, "flood")["bread"] == 5   # 11 // 2
    assert apply_event({"bread": 8, "buildings": []}, "calm")["bread"] == 8     # unknown -> unchanged


def test_fox_clamps_and_does_not_mutate_input():
    state = {"bread": 3, "buildings": [{"kind": "nest"}]}
    out = apply_event(state, "fox")
    assert out["bread"] == 0                          # 3 - 5 clamped
    assert state["bread"] == 3                         # input unchanged (new state returned)
    assert out["buildings"] == [{"kind": "nest"}]      # buildings preserved
