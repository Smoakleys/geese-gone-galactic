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
    # A sun + soft ambient so the low-poly shapes are LIT (gradients on spheres, face-shading on boxes) --
    # this reads as 3D depth instead of flat cut-outs. Ambient keeps shadowed sides visible, not black.
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-50, -40, 0)
    add_child(sun)
    var worldenv := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color(0.2, 0.2, 0.22)
    env.ambient_light_color = Color(0.55, 0.55, 0.6)
    env.ambient_light_energy = 0.6
    worldenv.environment = env
    add_child(worldenv)
    build(self)

'''

_HELPERS = '''
func _mat(color):
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.roughness = 0.9
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
    mi.material_override = _mat(color)
    root.add_child(mi)
    return mi   # position via the args; the node is returned too (use .position, NOT .translation, in Godot 4)

# Helper: add a box (building) of `size` at `pos`.
func add_box(root, size, color, pos = Vector3.ZERO):
    var sz = size if (size is Vector3) else Vector3(float(size), float(size), float(size))
    var mi := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = sz
    mi.mesh = bm
    mi.position = pos
    mi.material_override = _mat(color)
    root.add_child(mi)
    return mi

# Helper: add a SPHERE (rounded shape -- a goose body/head, a berry) of radius `r` at `pos`.
func add_sphere(root, r, color, pos = Vector3.ZERO):
    var mi := MeshInstance3D.new()
    var sm := SphereMesh.new()
    sm.radius = float(r)
    sm.height = float(r) * 2.0
    mi.mesh = sm
    mi.position = pos
    mi.material_override = _mat(color)
    root.add_child(mi)
    return mi

'''

# High-level PROP helpers: one call builds a whole modelled goose or building (see game/godot/models.py for
# the same shapes). This is how Icarus builds GOOD scenes cheaply -- `add_goose(root, Vector3(x,0,z))` and
# `add_building(root, "bakery", Vector3(x,0,z))` instead of hand-placing dozens of primitives. Backed by
# rich mesh makers (cone/prism/scaled+rotated) the plain add_box/add_sphere don't provide.
_MODEL_HELPERS = '''
func _part(root, mesh, color, pos, scl = Vector3.ONE, rot = Vector3.ZERO):
    var mi := MeshInstance3D.new()
    mi.mesh = mesh
    mi.position = pos
    mi.scale = scl
    mi.rotation_degrees = rot
    mi.material_override = _mat(color)
    root.add_child(mi)
    return mi

func _boxm(sz):
    var m := BoxMesh.new()
    m.size = sz
    return m

func _cone(br, h):
    var m := CylinderMesh.new()
    m.top_radius = 0.0
    m.bottom_radius = br
    m.height = h
    m.radial_segments = 24
    return m

func _cyl(r, h):
    var m := CylinderMesh.new()
    m.top_radius = r
    m.bottom_radius = r
    m.height = h
    m.radial_segments = 24
    return m

func _prism(sz):
    var m := PrismMesh.new()
    m.size = sz
    return m

func _ball(r):
    var m := SphereMesh.new()
    m.radius = r
    m.height = r * 2.0
    m.radial_segments = 24
    m.rings = 12
    return m

# A stylized goose at `pos`, scaled by `s`, facing -X (f=-1.0) or +X (f=1.0).
func add_goose(root, pos, s = 1.0, f = -1.0):
    var white = Color(0.97, 0.97, 0.94)
    var wingc = Color(0.88, 0.88, 0.85)
    var beak = Color(0.96, 0.55, 0.08)
    var dark = Color(0.05, 0.05, 0.05)
    _part(root, _ball(1.0), white, pos + Vector3(0, 1.0, 0) * s, Vector3(1.7, 1.0, 1.15) * s)
    _part(root, _cone(0.32, 0.75), white, pos + Vector3(f * 1.55, 1.4, 0) * s, Vector3.ONE * s, Vector3(0, 0, f * -52))
    _part(root, _ball(0.9), wingc, pos + Vector3(f * 0.15, 1.25, 0.72) * s, Vector3(1.5, 0.8, 0.5) * s, Vector3(0, f * -14, 10))
    _part(root, _ball(0.9), wingc, pos + Vector3(f * 0.15, 1.25, -0.72) * s, Vector3(1.5, 0.8, 0.5) * s, Vector3(0, f * 14, 10))
    var nc = [Vector3(1.2, 1.5, 0), Vector3(1.4, 1.85, 0), Vector3(1.55, 2.2, 0), Vector3(1.62, 2.55, 0), Vector3(1.58, 2.9, 0), Vector3(1.65, 3.2, 0), Vector3(1.85, 3.42, 0), Vector3(2.08, 3.5, 0)]
    var pts = []
    for i in nc.size() - 1:
        for k in range(3):
            pts.append(nc[i].lerp(nc[i + 1], k / 3.0))
    pts.append(nc[nc.size() - 1])
    for j in pts.size():
        var q = pts[j]
        _part(root, _ball(0.40 - 0.13 * (float(j) / (pts.size() - 1))), white, pos + Vector3(f * q.x, q.y, q.z) * s, Vector3.ONE * s)
    _part(root, _ball(0.44), white, pos + Vector3(f * 2.28, 3.55, 0) * s, Vector3.ONE * s)
    _part(root, _cone(0.2, 0.66), beak, pos + Vector3(f * 2.82, 3.49, 0) * s, Vector3.ONE * s, Vector3(0, 0, 90))
    for z in [0.3, -0.3]:
        _part(root, _ball(0.08), dark, pos + Vector3(f * 2.46, 3.7, z) * s, Vector3.ONE * s)
        _part(root, _ball(0.03), Color.WHITE, pos + Vector3(f * 2.6, 3.75, z) * s, Vector3.ONE * s)

func add_bakery(root, pos):
    _part(root, _boxm(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), pos + Vector3(0, 0.6, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), pos + Vector3(0, 1.68, 0))
    _part(root, _boxm(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), pos + Vector3(0.5, 1.9, -0.3))
    _part(root, _boxm(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), pos + Vector3(0, 0.33, 0.71))

func add_granary(root, pos):
    _part(root, _cyl(0.75, 1.7), Color(0.85, 0.7, 0.45), pos + Vector3(0, 0.85, 0))
    _part(root, _cone(0.95, 0.8), Color(0.72, 0.26, 0.2), pos + Vector3(0, 2.1, 0))
    _part(root, _cyl(0.78, 0.12), Color(0.55, 0.36, 0.22), pos + Vector3(0, 1.2, 0))

func add_nest(root, pos):
    _part(root, _cyl(0.7, 0.35), Color(0.55, 0.36, 0.22), pos + Vector3(0, 0.18, 0))
    _part(root, _cyl(0.45, 0.25), Color(0.4, 0.28, 0.16), pos + Vector3(0, 0.32, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), pos + Vector3(-0.15, 0.42, 0.1))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), pos + Vector3(0.18, 0.42, -0.05))

func add_well(root, pos):
    _part(root, _cyl(0.55, 0.7), Color(0.62, 0.62, 0.6), pos + Vector3(0, 0.35, 0))
    _part(root, _boxm(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), pos + Vector3(-0.45, 0.9, 0))
    _part(root, _boxm(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), pos + Vector3(0.45, 0.9, 0))
    _part(root, _prism(Vector3(1.3, 0.4, 0.9)), Color(0.72, 0.26, 0.2), pos + Vector3(0, 1.55, 0))

func add_fence(root, pos):
    for dx in [-0.6, 0.0, 0.6]:
        _part(root, _boxm(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), pos + Vector3(dx, 0.35, 0))
    _part(root, _boxm(Vector3(1.4, 0.12, 0.08)), Color(0.55, 0.36, 0.22), pos + Vector3(0, 0.5, 0))

# A round bushy tree (scenery) at `pos`, scaled by `s`.
func add_tree(root, pos, s = 1.0):
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), pos + Vector3(0, 0.55, 0) * s, Vector3.ONE * s)
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), pos + Vector3(0, 1.5, 0) * s, Vector3.ONE * s)
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), pos + Vector3(0.28, 2.05, 0.1) * s, Vector3.ONE * s)
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), pos + Vector3(-0.3, 1.95, -0.1) * s, Vector3.ONE * s)

func add_building(root, kind, pos):
    match kind:
        "bakery": add_bakery(root, pos)
        "granary": add_granary(root, pos)
        "nest": add_nest(root, pos)
        "well": add_well(root, pos)
        "fence": add_fence(root, pos)
        "tree": add_tree(root, pos)
        _: add_bakery(root, pos)

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
    return _CAMERA + _HELPERS + _MODEL_HELPERS + _sanitize(build_fn).strip("\n") + "\n"


def _sanitize(build_fn: str) -> str:
    """The helpers are FILE-LEVEL, so fix the ways a small model wrongly reaches for them: drop any
    ``var x = preload/load(...)`` line, and strip an object prefix on a helper call
    (``helpers.add_plane`` / ``self.add_box`` -> ``add_plane`` / ``add_box``)."""
    fn = re.sub(r"(?m)^\s*var\s+\w+\s*=\s*(?:preload|load)\([^\n]*\n", "", build_fn)
    fn = re.sub(r"\b[A-Za-z_]\w*\.(add_plane|add_box|add_sphere|add_goose|add_building|"
                r"add_bakery|add_granary|add_nest|add_well|add_fence|add_tree)\b", r"\1", fn)
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
