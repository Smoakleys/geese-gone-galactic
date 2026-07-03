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


def _geese_lines(buildings: "list[dict]") -> "list[str]":
    """A little white goose (body + head + orange beak spheres) beside each nest -- geese live by their
    nests, so a rendered state shows the flock, not just the buildings. One per nest (goose_count is 4/nest,
    too many to draw legibly)."""
    lines: "list[str]" = []
    for b in buildings:
        if b.get("kind") == "nest":
            bx, bz = b["x"] * 2 + 1.2, b["y"] * 2               # beside the nest box (build_body: x*2,z*2)
            lines.append(f"\tadd_sphere(root, 0.35, Color.WHITE, Vector3({bx}, 0.35, {bz}))")
            lines.append(f"\tadd_sphere(root, 0.2, Color.WHITE, Vector3({bx}, 0.75, {bz - 0.25}))")
            lines.append(f"\tadd_box(root, Vector3(0.16, 0.1, 0.1), Color(1, 0.5, 0), "
                         f"Vector3({bx}, 0.75, {bz - 0.5}))")
    return lines


def pond_state_to_scene_gd(state: dict) -> str:
    """Compose a full lit ``scene.gd`` that renders ``state``'s buildings + geese on land + a pond."""
    buildings = state.get("buildings", [])
    body = build_body(buildings)
    content = [
        "func build(root: Node3D) -> void:",
        "\tadd_plane(root, Vector2(16, 16), Color.GREEN)",   # land
        "\tadd_plane(root, Vector2(6, 6), Color.BLUE, 0.1)",  # pond
    ]
    content += ["\t" + ln for ln in body.splitlines() if ln.strip()]
    content += _geese_lines(buildings)                        # a goose beside each nest
    return compose_scene("\n".join(content))


def render_pond_state(state: dict, out_png: "str | Path") -> "tuple[bool, str]":
    """Render a pond ``state`` to ``out_png`` as a lit 3D scene. Returns (ok, detail); never raises."""
    scene = pond_state_to_scene_gd(state)
    work = Path(tempfile.mkdtemp(prefix="pond_view_"))
    gd = work / "scene.gd"
    gd.write_text(scene, encoding="utf-8")
    return render_gdscript(gd, Path(out_png))
