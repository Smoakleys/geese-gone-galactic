"""Scene template — a known-good camera skeleton so the FAST, resident model can build scenes.

The offloaded 30B is the only local model that frames a scene unaided, but it is a 20GB model on a 16GB
card → permanently slow (see docs/SPEED.md). The framing (current orthographic camera aimed at the
origin) is exactly the part small resident models get wrong. So we GIVE that part: Icarus writes only a
``func build(root: Node3D) -> void:`` that adds meshes, and ``compose_scene`` wraps it with the camera.
The fast gpt-oss:20b can then build real scenes ~3-5x faster. This is a curated scaffold, not the answer
(Icarus still decides content/layout), and it is measured against the same render gate.
"""

from __future__ import annotations

# 4-space indented on purpose: the local models emit 4-space GDScript, and a scene may not mix tabs and
# spaces. compose_scene normalises the content to match so the wrapped file always has one indent style.
_HEAD = '''extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(12, 12, 12)
    cam.look_at(Vector3.ZERO, Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 18
    cam.current = true
    build(self)

'''


def _tabs_to_spaces(gd: str) -> str:
    out = []
    for line in gd.splitlines():
        stripped = line.lstrip("\t")
        out.append("    " * (len(line) - len(stripped)) + stripped)
    return "\n".join(out)


def compose_scene(build_gd: str) -> str:
    """Wrap Icarus's ``func build(root: Node3D)`` with the camera template into a full scene.gd.

    Indentation is normalised to 4 spaces so the composed file never mixes tabs and spaces (a Godot
    parse error). If the content omits the function header, it is treated as the function body."""
    body = _tabs_to_spaces(build_gd).strip("\n")
    if "func build" not in body:
        indented = "\n".join(("    " + ln) if ln.strip() else ln for ln in body.splitlines())
        body = "func build(root: Node3D) -> void:\n" + indented
    return _HEAD + body + "\n"
