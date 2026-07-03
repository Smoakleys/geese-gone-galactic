"""The art-generation pipeline (ops/generate_art.py) -- offline logic only (no network in the suite)."""

from __future__ import annotations

import io

import pytest

from ops.generate_art import ASSETS, _url, cutout


def test_manifest_covers_the_game_props():
    # every pond building kind + the goose + scenery must have a prompt, so the whole game can be re-skinned.
    for kind in ("bakery", "granary", "nest", "well", "fence"):
        assert kind in ASSETS, kind
    for extra in ("goose", "tree", "pond", "ground"):
        assert extra in ASSETS, extra
    assert all(isinstance(p, str) and len(p) > 10 for p in ASSETS.values())


def test_url_is_a_valid_pollinations_request():
    u = _url("a goose", seed=7, w=640, h=640)
    assert u.startswith("https://image.pollinations.ai/prompt/")
    assert "width=640" in u and "height=640" in u and "seed=7" in u
    assert "a%20goose" in u or "a goose".replace(" ", "%20") in u        # prompt url-encoded


def test_cutout_makes_white_background_transparent():
    from PIL import Image
    im = Image.new("RGBA", (40, 40), (255, 255, 255, 255))    # all white
    for x in range(14, 26):                                    # a solid colored blob in the middle
        for y in range(14, 26):
            im.putpixel((x, y), (200, 60, 40, 255))
    buf = io.BytesIO(); im.save(buf, "PNG")
    out = Image.open(io.BytesIO(cutout(buf.getvalue()))).convert("RGBA")
    assert out.getpixel((0, 0))[3] == 0                        # border white -> transparent
    assert out.getpixel((39, 39))[3] == 0
    assert out.getpixel((20, 20))[3] == 255                    # the blob stays opaque


def test_cutout_keeps_interior_white_of_an_enclosed_shape():
    # flood fill is from the BORDER, so white fully enclosed by colour is NOT cleared (e.g. a window).
    from PIL import Image
    im = Image.new("RGBA", (30, 30), (255, 255, 255, 255))
    for x in range(8, 22):                                     # a colored ring with white inside
        im.putpixel((x, 8), (0, 0, 0, 255)); im.putpixel((x, 21), (0, 0, 0, 255))
    for y in range(8, 22):
        im.putpixel((8, y), (0, 0, 0, 255)); im.putpixel((21, y), (0, 0, 0, 255))
    buf = io.BytesIO(); im.save(buf, "PNG")
    out = Image.open(io.BytesIO(cutout(buf.getvalue()))).convert("RGBA")
    assert out.getpixel((0, 0))[3] == 0                        # outside cleared
    assert out.getpixel((15, 15))[3] == 255                    # enclosed white kept
