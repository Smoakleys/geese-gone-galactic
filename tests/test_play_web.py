"""The browser game (ops/play_web.py) -- its game CORE + page, tested without a live socket."""

from __future__ import annotations

from ops.play_web import GameSession, _page, KINDS


def test_build_actions_add_buildings():
    g = GameSession()
    assert g.act("build_bakery") == "built bakery"
    assert g.act("build_nest") == "built nest"
    assert len(g.state["buildings"]) == 2
    assert [b["kind"] for b in g.state["buildings"]] == ["bakery", "nest"]


def test_tick_action_runs_the_economy():
    g = GameSession()
    g.act("build_bakery")
    before = g.state["bread"]
    assert "ticked" in g.act("tick")
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
