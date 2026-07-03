"""Scene template — a known-good camera skeleton so the FAST, resident model can build scenes.

The offloaded 30B is the only local model that frames a scene unaided, but it is a 20GB model on a 16GB
card → permanently slow (see docs/SPEED.md). The framing (current orthographic camera aimed at the
origin) is exactly the part small resident models get wrong. So we GIVE that part: Icarus writes only a
``func build(root: Node3D) -> void:`` that adds meshes, and ``compose_scene`` wraps it with the camera.
The fast gpt-oss:20b can then build real scenes ~3-5x faster. This is a curated scaffold, not the answer
(Icarus still decides content/layout), and it is measured against the same render gate.
"""

from __future__ import annotations

from pathlib import Path

# 4-space indented on purpose: the local models emit 4-space GDScript, and a scene may not mix tabs and
# spaces. compose_scene normalises the content to match so the wrapped file always has one indent style.
_CAMERA = '''extends Node3D

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

_HELPERS = '''
func _unshaded(color: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    m.albedo_color = color
    return m

# Helper: add a FLAT horizontal plane (already in the XZ plane -- never rotate it). `y` layers it.
func add_plane(root: Node3D, size: Vector2, color: Color, y: float = 0.0) -> void:
    var mi := MeshInstance3D.new()
    var pm := PlaneMesh.new()
    pm.size = size
    mi.mesh = pm
    mi.position = Vector3(0, y, 0)
    mi.material_override = _unshaded(color)
    root.add_child(mi)

# Helper: add a box (building) of `size` at `pos`.
func add_box(root: Node3D, size: Vector3, color: Color, pos: Vector3) -> void:
    var mi := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = size
    mi.mesh = bm
    mi.position = pos
    mi.material_override = _unshaded(color)
    root.add_child(mi)

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
    # Only inject the template helpers if the content did NOT define its own -- a local model sometimes
    # redefines add_plane/add_box despite instructions, and duplicate function defs are a Godot parse
    # error (which blanked the render). Camera is always ours; helpers are opt-in by absence.
    self_contained = "func add_plane" in body or "func add_box" in body or "func _unshaded" in body
    head = _CAMERA if self_contained else _CAMERA + _HELPERS
    return head + body + "\n"


def materialize_templated_scene(artifact_dir: "Path | str") -> None:
    """Post-build hook: if Icarus wrote a ``func build(root)`` (templated content) but no full
    ``scene.gd``, compose one from it + the camera template so the standard Godot checks gate a complete
    scene. No-op if a scene.gd already exists or no build() content is found (harmless on any artifact)."""
    d = Path(artifact_dir)
    if (d / "scene.gd").exists():
        return
    for p in sorted(d.rglob("*.gd")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if "func build" in text:
            (d / "scene.gd").write_text(compose_scene(text), encoding="utf-8")
            return
