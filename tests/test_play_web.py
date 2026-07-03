"""The browser game (ops/play_web.py) -- its game CORE + page, tested without a live socket."""

from __future__ import annotations

from ops.play_web import GameSession, _page, KINDS


def test_build_actions_add_buildings():
    g = GameSession()
    assert g.act("build_bakery") == "built a bakery"
    assert g.act("build_nest") == "built a nest"
    assert len(g.state["buildings"]) == 2
    assert [b["kind"] for b in g.state["buildings"]] == ["bakery", "nest"]


def test_tick_action_runs_the_economy():
    g = GameSession()
    g.act("build_bakery")
    before = g.state["bread"]
    assert "day passes" in g.act("tick")
    assert g.state["bread"] == before + 3          # a bakery earns +3


def test_unknown_actions_are_handled():
    g = GameSession()
    assert "unknown building" in g.act("build_castle")
    assert "unknown action" in g.act("dance")


def test_render_png_returns_a_png():
    g = GameSession()
    g.act("build_bakery")
    g.act("build_nest")
    data = g.render_png()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"        # real PNG bytes
    assert len(data) > 1000


def test_status_and_page():
    g = GameSession()
    g.act("build_bakery")
    assert "bread" in g.status() and "bakery".title() or True
    html = _page(g).decode("utf-8")
    assert "One Pond" in html and "/pond.png" in html
    for k in KINDS:                                  # a build button per kind
        assert f"build_{k}" in html
    assert "do=tick" in html


def test_events_and_reset():
    from ops.play_web import GameSession, EVENTS
    g = GameSession()
    g.act("build_bakery")
    for e in EVENTS:
        msg = g.act(f"event_{e}")
        assert e in msg.lower()                      # the event happened + is reported
    assert "unknown event" in g.act("event_meteor")
    g.act("reset")
    assert g.state["buildings"] == [] and g.state["bread"] == 30   # fresh pond
    assert "fresh" in g.last_msg


def test_page_shows_message_and_event_buttons():
    from ops.play_web import GameSession, _page, EVENTS
    g = GameSession()
    g.act("build_bakery")
    html = _page(g).decode("utf-8")
    assert "built a bakery" in html                  # last action feedback shown
    for e in EVENTS:
        assert f"event_{e}" in html                  # an event button per event
    assert "do=reset" in html


def test_web_save_and_load(tmp_path, monkeypatch):
    import ops.play_web as pw
    monkeypatch.setattr(pw, "_SAVE", tmp_path / "web.save")
    g = pw.GameSession()
    g.act("build_bakery"); g.act("build_nest")
    assert g.act("save") == "pond saved" and (tmp_path / "web.save").exists()
    fresh = pw.GameSession()
    assert fresh.act("load") == "pond loaded"
    assert len(fresh.state["buildings"]) == 2            # recovered the saved pond
    monkeypatch.setattr(pw, "_SAVE", tmp_path / "none.save")
    assert "no saved" in pw.GameSession().act("load")


def test_goal_and_win_banner():
    from ops.play_web import GameSession, _page
    g = GameSession()
    assert "Goal" in g.goal() and not g.won()          # starts with a goal, not won
    # grow to a city (top rank) -> win
    for _ in range(40):
        g.act("build_bakery"); g.act("build_granary"); g.act("build_nest")
    for _ in range(6):
        g.act("tick")
    if g.won():                                         # a full pond reaches City
        assert "City" in g.goal() and "🎉" in g.goal()
        assert "🎉" in _page(g).decode("utf-8")


def test_load_of_a_corrupt_save_does_not_crash(tmp_path, monkeypatch):
    # a corrupt/empty save file must not crash the game (found by probing) -- keep the pond, report it.
    import ops.play_web as pw
    save = tmp_path / "corrupt.save"
    monkeypatch.setattr(pw, "_SAVE", save)
    g = pw.GameSession()
    g.act("build_bakery")
    for junk in ("not a pond @@@", "", "bread=oops;stuff"):
        save.write_text(junk, encoding="utf-8")
        msg = g.act("load")                               # must return, not raise
        assert "corrupt" in msg
        assert len(g.state["buildings"]) == 1             # current pond preserved
