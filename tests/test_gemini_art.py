"""ops/gemini_art.py -- offline logic (prompt building + key loading); the network call needs a key."""
from __future__ import annotations
from ops.gemini_art import build_prompt, load_key, ASSETS, STYLE


def test_prompt_locks_one_viewpoint_and_style():
    p = build_prompt("a goose")
    assert p.startswith("a goose")
    assert "3/4 top-down isometric" in p and "30-degree" in p            # locked viewpoint
    assert "top-left" in p and "white background" in p                   # locked light + clean bg
    # every asset prompt shares the exact same style suffix -> coherent set
    for desc in ASSETS.values():
        assert build_prompt(desc).endswith(STYLE)


def test_manifest_covers_every_prop():
    for k in ("goose", "bakery", "granary", "nest", "well", "fence", "tree", "pond", "ground"):
        assert k in ASSETS


def test_load_key_from_env(monkeypatch, tmp_path):
    import ops.gemini_art as g
    monkeypatch.setattr(g, "_CONFIG", tmp_path / "none.json")
    monkeypatch.setattr(g, "_KEYFILE", tmp_path / "none.txt")
    monkeypatch.setenv("GEMINI_API_KEY", "  test-key-123  ")
    assert load_key() == "test-key-123"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert load_key() is None                                            # no key configured -> None


def test_reference_prompt_is_a_full_scene_not_the_asset_style():
    # the discipline compares my scene to a REAL game screenshot -> reference must be a full scene, not a
    # single-asset white-bg prompt.
    from ops.gemini_art import REFERENCE_PROMPT
    assert "screenshot" in REFERENCE_PROMPT and "isometric" in REFERENCE_PROMPT
    assert "white background" not in REFERENCE_PROMPT                    # not the single-asset style


def test_image_request_retries_then_raises(monkeypatch):
    # a flaky endpoint must be retried (backoff), then surface the error -- not hang or swallow it.
    import ops.gemini_art as g
    calls = {"n": 0}
    def boom(*a, **k):
        calls["n"] += 1
        raise OSError("boom")
    monkeypatch.setattr(g.urllib.request, "urlopen", boom)
    monkeypatch.setattr(g.time if hasattr(g, "time") else __import__("time"), "sleep", lambda *_: None)
    import pytest as _pt
    with _pt.raises(OSError):
        g._image_request("p", "key", "model", timeout=1, retries=3)
    assert calls["n"] == 3                                              # retried the full budget


def test_generate_cuts_white_background_to_transparency(tmp_path, monkeypatch):
    # Gemini assets come on a white bg (per the prompt); generate() must cut them out so they composite.
    import io
    from PIL import Image
    import ops.gemini_art as g

    def fake_image(prompt, key, model, timeout, retries=3):
        buf = io.BytesIO()
        Image.new("RGBA", (24, 24), (255, 255, 255, 255)).save(buf, "PNG")   # all-white
        return buf.getvalue()
    monkeypatch.setattr(g, "_image_request", fake_image)
    out = tmp_path / "goose.png"
    assert g.generate("a goose", out, "key")
    corner = Image.open(out).convert("RGBA").getpixel((0, 0))
    assert corner[3] == 0                                                     # white bg cut to transparent
