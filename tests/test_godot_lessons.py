"""The durable Godot notebook loads with the distilled lessons."""

from __future__ import annotations

from game.godot.lessons import LESSONS_PATH, godot_notebook, godot_working_notebook


def test_godot_notebook_has_the_key_lessons():
    text = godot_notebook().read()
    assert text.strip()
    # the two gotchas that turn an empty render into a visible scene
    assert "look_at" in text
    assert "current" in text
    # framing guidance (general domain knowledge, not a per-ticket answer)
    assert "size" in text.lower()
    # Godot-4 API gotchas earned from a real blank OP-1 scene (lowercase Color / CubeMesh error at runtime)
    assert "Color.GREEN" in text
    assert "BoxMesh" in text
    # GDScript-for-local-models gotchas from the speed pass (no kwargs; position not translation)
    assert "keyword argument" in text
    assert "translation" in text


def test_godot_notebook_entries_are_nonempty():
    assert len(godot_notebook().entries()) >= 4


def test_working_notebook_is_isolated_from_the_seed(tmp_path):
    seed_before = LESSONS_PATH.read_text(encoding="utf-8")
    wb = godot_working_notebook(tmp_path)
    assert "look_at" in wb.read()                 # copy carries the lessons
    wb.append("a confused scratch note the model invented")
    # the working copy changed, but the committed seed did NOT (no pollution)
    assert "confused scratch note" in wb.read()
    assert LESSONS_PATH.read_text(encoding="utf-8") == seed_before
