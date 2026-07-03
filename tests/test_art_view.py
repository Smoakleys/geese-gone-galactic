"""The art composition layer (game/art_view.py) -- renders a state to an art PNG, robust to missing assets."""

from __future__ import annotations

from game.art_view import compose_pond_art
from game.pond import add_building


def test_compose_produces_a_nonblank_png(tmp_path):
    s = {"bread": 0, "buildings": []}
    for k, x, y in [("bakery", 1, 1), ("granary", 2, 1), ("nest", 3, 2), ("well", 1, 3)]:
        s = add_building(s, k, x, y, 8)
    out = compose_pond_art(s, tmp_path / "pond.png", size=(500, 380))
    assert out.exists()
    from PIL import Image, ImageStat
    im = Image.open(out).convert("RGB")
    assert max(ImageStat.Stat(im).stddev) > 4          # a pond + props -> real variation, not a flat fill


def test_compose_renders_even_with_no_buildings(tmp_path):
    out = compose_pond_art({"bread": 0, "buildings": []}, tmp_path / "empty.png", size=(300, 220))
    assert out.exists()                                 # always renders (ground + pond)


def test_missing_assets_degrade_to_placeholders_not_a_crash(tmp_path, monkeypatch):
    # point ART_DIR at an empty dir -> every sprite is missing -> placeholders, still renders.
    import game.art_view as av
    monkeypatch.setattr(av, "ART_DIR", tmp_path / "no_assets")
    s = add_building({"bread": 0, "buildings": []}, "nest", 2, 2, 8)   # a nest -> a goose too
    out = compose_pond_art(s, tmp_path / "ph.png", size=(300, 220))
    assert out.exists()
