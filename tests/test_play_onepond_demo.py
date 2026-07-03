"""The One Pond demo runs and shows both outcomes (smoke test of the runnable showcase)."""

from __future__ import annotations

from ops.play_onepond import play, play_neglected
from game.pond import pond_outcome


def test_demo_well_tended_pond_thrives():
    state = play(verbose=False)
    assert len(state["buildings"]) == 5
    assert pond_outcome(state, 2) == "thriving"


def test_demo_neglected_pond_suffers():
    state = play_neglected(verbose=False)
    assert pond_outcome(state, 2) == "dry"        # a bakery with no well -> the stakes are real
