"""The assembled Icarus builder factory wires all the pieces together."""

from __future__ import annotations

from game.icarus_builder import default_icarus_builder


def test_default_icarus_builder_is_routed_and_equipped(tmp_path):
    b = default_icarus_builder(tmp_path)
    # routed across the fast + big models
    assert b.id.startswith("icarus-agent:routed(")
    assert "gpt-oss:20b" in b.id and "qwen3:30b" in b.id
    # equipped with render + vision + a working notebook copy (curated lessons, isolated from the seed)
    assert b._render_fn is not None
    assert b._vision is not None
    assert "look_at" in b._notebook.read()
    assert (tmp_path / "godot_notebook.md").exists()
