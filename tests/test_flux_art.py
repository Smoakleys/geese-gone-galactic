"""ops/flux_art.py — offline logic (keyless generator; the network call is exercised live, not in tests)."""
from __future__ import annotations
from ops.flux_art import build_prompt, ASSETS, STYLE


def test_prompt_locks_one_isometric_viewpoint():
    p = build_prompt("a goose")
    assert p.startswith("a goose")
    assert "isometric" in p and "30 degree" in p          # locked viewpoint
    assert "white background" in p
    for desc in ASSETS.values():                          # every asset shares the exact style suffix
        assert build_prompt(desc).endswith(STYLE)


def test_manifest_covers_every_prop():
    for k in ("goose", "bakery", "granary", "nest", "well", "fence", "tree", "pond", "ground"):
        assert k in ASSETS
