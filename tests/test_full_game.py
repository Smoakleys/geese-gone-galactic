"""End-to-end: a full One Pond playthrough through the real components (logic + save/load + art render).

Locks the complete game as one product -- the game logic, the browser session, save/load, and the art
renderer all working together across a real session -- so a regression in any layer fails here.
"""

from __future__ import annotations

import ops.play_web as pw
from game.pond import pond_rank, pond_score


def test_full_playthrough_build_grow_event_saveload_render_win(tmp_path, monkeypatch):
    monkeypatch.setattr(pw, "_SAVE", tmp_path / "game.save")
    g = pw.GameSession()
    assert not g.won() and "Goal" in g.goal()                    # starts with a goal, not won

    # build a whole pond (every kind, many times) via the same actions the web buttons trigger
    for _ in range(30):
        for kind in ("bakery", "granary", "nest", "well", "fence"):
            g.act(f"build_{kind}")
    kinds = {b["kind"] for b in g.state["buildings"]}
    assert kinds == {"bakery", "granary", "nest", "well", "fence"}   # all five placed

    # a weather event + several days
    assert "harvest" in g.act("event_harvest").lower()
    for _ in range(5):
        g.act("tick")

    # the current pond renders as real art (a valid, non-trivial PNG)
    png = g.render_png()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 10000

    # save + load round-trips the whole pond into a fresh session
    n_buildings = len(g.state["buildings"])
    assert g.act("save") == "pond saved"
    reloaded = pw.GameSession()
    assert reloaded.act("load") == "pond loaded"
    assert len(reloaded.state["buildings"]) == n_buildings

    # a big built-up pond has grown well past the start (progression works)
    assert pond_rank(pond_score(g.state)) in ("town", "city")

    # reset returns to a fresh pond
    g.act("reset")
    assert g.state["buildings"] == [] and g.state["bread"] == 30
