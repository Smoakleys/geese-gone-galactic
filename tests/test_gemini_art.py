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
