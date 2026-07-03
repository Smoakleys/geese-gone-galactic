"""Render an actual pond STATE to a lit 3D image — the logic→visual bridge, packaged.

The two halves of the game were built separately: `game/pond` is the simulation (a state = bread +
buildings), and `game/godot` renders hand-authored scenes. This connects them: `build_body` turns a
state's buildings into `add_box` statements, the lit scene template wraps them with land + pond + camera +
lighting, and we render a PNG. So a PLAYED game — the state you actually reached — can be SEEN as a 3D
scene, not just the static authored scenes. Every produced scene still clears the same `godot_render` gate.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from game.godot.capture import render_gdscript
from game.godot.scene_template import compose_scene
from game.pond.pond_scene import build_body


def pond_state_to_scene_gd(state: dict) -> str:
    """Compose a full lit ``scene.gd`` that renders ``state``'s buildings on land + a pond."""
    body = build_body(state.get("buildings", []))
    content = [
        "func build(root: Node3D) -> void:",
        "\tadd_plane(root, Vector2(16, 16), Color.GREEN)",   # land
        "\tadd_plane(root, Vector2(6, 6), Color.BLUE, 0.1)",  # pond
    ]
    content += ["\t" + ln for ln in body.splitlines() if ln.strip()]
    return compose_scene("\n".join(content))


def render_pond_state(state: dict, out_png: "str | Path") -> "tuple[bool, str]":
    """Render a pond ``state`` to ``out_png`` as a lit 3D scene. Returns (ok, detail); never raises."""
    scene = pond_state_to_scene_gd(state)
    work = Path(tempfile.mkdtemp(prefix="pond_view_"))
    gd = work / "scene.gd"
    gd.write_text(scene, encoding="utf-8")
    return render_gdscript(gd, Path(out_png))
