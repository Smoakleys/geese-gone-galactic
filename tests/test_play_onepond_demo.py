"""The One Pond demo runs and produces a thriving pond (smoke test of the runnable showcase)."""

from __future__ import annotations

from ops.play_onepond import play
from game.pond import pond_outcome


def test_demo_plays_to_a_thriving_pond():
    state = play(verbose=False)
    assert len(state["buildings"]) == 5
    assert pond_outcome(state, 2) == "thriving"
