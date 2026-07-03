"""Scene template — a known-good camera skeleton so the FAST, resident model can build scenes.

The offloaded 30B is the only local model that frames a scene unaided, but it is a 20GB model on a 16GB
card → permanently slow (see docs/SPEED.md). The framing (current orthographic camera aimed at the
origin) is exactly the part small resident models get wrong. So we GIVE that part: Icarus writes only a
``func build(root: Node3D) -> void:`` that adds meshes, and ``compose_scene`` wraps it with the camera.
The fast gpt-oss:20b can then build real scenes ~3-5x faster. This is a curated scaffold, not the answer
(Icarus still decides content/layout), and it is measured against the same render gate.
"""

from __future__ import annotations

import re
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
func _unshaded(color):
    var m := StandardMaterial3D.new()
    m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    m.albedo_color = color
    return m

# Helper: add a FLAT horizontal plane (already in the XZ plane -- never rotate it). `y` layers it.
# Params are untyped + coercing on purpose: a small local model often passes a scalar for `size` or omits
# args, and a typed signature turns that into a parse error that blanks the whole scene.
func add_plane(root, size, color, y = 0.0):
    var sz = size if (size is Vector2) else Vector2(float(size), float(size))
    var mi := MeshInstance3D.new()
    var pm := PlaneMesh.new()
    pm.size = sz
    mi.mesh = pm
    mi.position = Vector3(0, y, 0)
    mi.material_override = _unshaded(color)
    root.add_child(mi)

# Helper: add a box (building) of `size` at `pos`.
func add_box(root, size, color, pos = Vector3.ZERO):
    var sz = size if (size is Vector3) else Vector3(float(size), float(size), float(size))
    var mi := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = sz
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


def _extract_build_func(gd: str) -> "str | None":
    """Pull just the top-level ``func build(...)`` block out of the content, dropping everything else
    (a stray ``extends`` header, buggy helper redefinitions). Returns None if there is no build()."""
    lines = gd.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("func build")), None)
    if start is None:
        return None
    out = [lines[start]]
    for ln in lines[start + 1:]:
        if ln[:1] not in ("", " ", "\t") and ln.lstrip().startswith("func "):
            break                                   # next top-level function -> build() block ended
        out.append(ln)
    return "\n".join(out).rstrip("\n")


def compose_scene(build_gd: str) -> str:
    """Wrap Icarus's scene CONTENT with the camera template + correct helpers into a full scene.gd.

    Robust to a local model writing more than asked: we extract only its ``func build(root)`` and always
    provide OUR camera + OUR add_plane/add_box, discarding any stray ``extends`` line or buggy helper
    redefinitions the model added (both are Godot parse/runtime errors that blank the render).
    Indentation is normalised to 4 spaces so the file never mixes tabs and spaces."""
    body = _tabs_to_spaces(build_gd)
    build_fn = _extract_build_func(body)
    if build_fn is None:
        stmts = [ln for ln in body.splitlines() if not ln.strip().startswith("extends")]
        indented = "\n".join(("    " + ln) if ln.strip() else ln for ln in stmts)
        build_fn = "func build(root: Node3D) -> void:\n" + indented
    return _CAMERA + _HELPERS + _sanitize(build_fn).strip("\n") + "\n"


def _sanitize(build_fn: str) -> str:
    """The helpers are FILE-LEVEL, so fix the ways a small model wrongly reaches for them: drop any
    ``var x = preload/load(...)`` line, and strip an object prefix on a helper call
    (``helpers.add_plane`` / ``self.add_box`` -> ``add_plane`` / ``add_box``)."""
    fn = re.sub(r"(?m)^\s*var\s+\w+\s*=\s*(?:preload|load)\([^\n]*\n", "", build_fn)
    fn = re.sub(r"\b[A-Za-z_]\w*\.(add_plane|add_box)\b", r"\1", fn)
    # GDScript has NO keyword arguments -- a small model writes Python-isms like add_plane(..., y=0.1)
    # or pos=Vector3(...), which are parse errors. Strip a `name=` that appears as a call argument.
    fn = re.sub(r"([(,]\s*)[A-Za-z_]\w*\s*=\s*(?!=)", r"\1", fn)
    return fn


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
            # Remove the incomplete source: it CALLS add_plane/add_box without defining them, so
            # godot_parse (which checks every .gd) would reject it and fail the whole artifact. Only the
            # composed scene.gd should be gated.
            if p.resolve() != (d / "scene.gd").resolve():
                p.unlink(missing_ok=True)
            return
