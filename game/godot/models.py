"""Reusable low-poly MODELS for GGG scenes -- a goose and the pond buildings, emitted as GDScript.

The whole game shares one look: instead of plain coloured boxes, every building is a little modelled prop
(a roofed bakery, a silo granary, a nest with eggs, a roofed well, a fence) and geese are proper geese
(plump body, S-neck, beak, eye, wings, tail). This module emits the GDScript for those props so BOTH the
authored showcase scenes and the played-state renderer (`pond_view`) draw them the same way.

Each ``*_lines(base)`` returns GDScript statements that call the rich ``_part/_box/_cyl/_cone/_prism/_ball``
helpers in ``MODEL_HELPERS``; ``compose_model_scene`` wraps a body with a lit camera + those helpers into a
full, renderable ``scene.gd``. Positions are emitted as absolute Vector3 literals (deterministic + testable).
"""

from __future__ import annotations

# Rich primitive helpers (scaled/rotated meshes, cones, prisms) injected into every model scene. These are
# a superset of the scene_template helpers -- models need cones (beaks/roofs), prisms (gables) and per-part
# scale+rotation (ellipsoid bodies, tilted roofs) that add_box/add_sphere don't provide.
MODEL_HELPERS = '''
func _mat(color, rough = 0.85):
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.roughness = rough
    return m

func _part(root, mesh, color, pos, scl = Vector3.ONE, rot = Vector3.ZERO):
    var mi := MeshInstance3D.new()
    mi.mesh = mesh
    mi.position = pos
    mi.scale = scl
    mi.rotation_degrees = rot
    mi.material_override = _mat(color)
    root.add_child(mi)
    return mi

func _box(sz):
    var m := BoxMesh.new()
    m.size = sz
    return m

func _cyl(r, h):
    var m := CylinderMesh.new()
    m.top_radius = r
    m.bottom_radius = r
    m.height = h
    m.radial_segments = 24
    return m

func _cone(br, h):
    var m := CylinderMesh.new()
    m.top_radius = 0.0
    m.bottom_radius = br
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
'''

# -- palette --------------------------------------------------------------------------
GRASS = "Color(0.42, 0.62, 0.32)"
POND = "Color(0.28, 0.52, 0.72)"
SKY = "Color(0.53, 0.81, 0.92)"
_WALL = "Color(0.93, 0.85, 0.62)"
_ROOF = "Color(0.72, 0.26, 0.2)"
_WOOD = "Color(0.55, 0.36, 0.22)"
_STONE = "Color(0.62, 0.62, 0.6)"
_TAN = "Color(0.85, 0.7, 0.45)"
_WHITE = "Color(0.97, 0.97, 0.94)"
_WINGC = "Color(0.88, 0.88, 0.85)"
_BEAK = "Color(0.96, 0.55, 0.08)"
_DARK = "Color(0.05, 0.05, 0.05)"
_EGG = "Color(0.96, 0.95, 0.9)"


def _v(x, y, z) -> str:
    return f"Vector3({x:g}, {y:g}, {z:g})"


def _part(mesh: str, color: str, pos, scl=(1, 1, 1), rot=(0, 0, 0)) -> str:
    # 4-space indent (never tabs): a scene may not mix tab + space indentation, and the template header is
    # space-indented, so every emitted statement uses spaces too.
    return f"    _part(root, {mesh}, {color}, {_v(*pos)}, {_v(*scl)}, {_v(*rot)})"


def _at(base, dx, dy, dz):
    return (base[0] + dx, base[1] + dy, base[2] + dz)


# -- buildings ------------------------------------------------------------------------

def bakery_lines(base) -> "list[str]":
    return [
        _part("_box(Vector3(1.6, 1.2, 1.4))", _WALL, _at(base, 0, 0.6, 0)),
        _part("_prism(Vector3(1.9, 0.95, 1.6))", _ROOF, _at(base, 0, 1.68, 0)),
        _part("_box(Vector3(0.25, 0.55, 0.25))", _STONE, _at(base, 0.5, 1.9, -0.3)),
        _part("_box(Vector3(0.45, 0.65, 0.06))", _WOOD, _at(base, 0, 0.33, 0.71)),
    ]


def granary_lines(base) -> "list[str]":
    return [
        _part("_cyl(0.75, 1.7)", _TAN, _at(base, 0, 0.85, 0)),
        _part("_cone(0.95, 0.8)", _ROOF, _at(base, 0, 2.1, 0)),
        _part("_cyl(0.78, 0.12)", _WOOD, _at(base, 0, 1.2, 0)),
    ]


def nest_lines(base) -> "list[str]":
    return [
        _part("_cyl(0.7, 0.35)", _WOOD, _at(base, 0, 0.18, 0)),
        _part("_cyl(0.45, 0.25)", "Color(0.4, 0.28, 0.16)", _at(base, 0, 0.32, 0)),
        _part("_ball(0.18)", _EGG, _at(base, -0.15, 0.42, 0.1)),
        _part("_ball(0.18)", _EGG, _at(base, 0.18, 0.42, -0.05)),
    ]


def well_lines(base) -> "list[str]":
    return [
        _part("_cyl(0.55, 0.7)", _STONE, _at(base, 0, 0.35, 0)),
        _part("_box(Vector3(0.1, 1.0, 0.1))", _WOOD, _at(base, -0.45, 0.9, 0)),
        _part("_box(Vector3(0.1, 1.0, 0.1))", _WOOD, _at(base, 0.45, 0.9, 0)),
        _part("_prism(Vector3(1.3, 0.4, 0.9))", _ROOF, _at(base, 0, 1.55, 0)),
    ]


def fence_lines(base) -> "list[str]":
    lines = [_part("_box(Vector3(0.12, 0.7, 0.12))", _WOOD, _at(base, dx, 0.35, 0))
             for dx in (-0.6, 0.0, 0.6)]
    lines.append(_part("_box(Vector3(1.4, 0.12, 0.08))", _WOOD, _at(base, 0, 0.5, 0)))
    return lines


_TRUNK = "Color(0.45, 0.31, 0.19)"
_LEAF = "Color(0.30, 0.52, 0.26)"
_LEAF2 = "Color(0.34, 0.57, 0.29)"


def tree_lines(base, s: float = 1.0) -> "list[str]":
    """A round bushy tree (trunk + two overlapping leaf blobs) at ``base``, scaled by ``s`` -- scenery so
    the world isn't just buildings on bare grass."""
    def p(dx, dy, dz):
        return _at(base, dx * s, dy * s, dz * s)

    return [
        _part("_cyl(0.16, 1.1)", _TRUNK, p(0, 0.55, 0), (s, s, s)),
        _part("_ball(0.85)", _LEAF, p(0, 1.5, 0), (s, s, s)),
        _part("_ball(0.62)", _LEAF2, p(0.28, 2.05, 0.1), (s, s, s)),
        _part("_ball(0.6)", _LEAF2, p(-0.3, 1.95, -0.1), (s, s, s)),
    ]


BUILDING_LINES = {
    "bakery": bakery_lines, "granary": granary_lines, "nest": nest_lines,
    "well": well_lines, "fence": fence_lines, "tree": tree_lines,
}


def building_lines(kind: str, base) -> "list[str]":
    """GDScript for a building of ``kind`` at ``base`` (falls back to a simple hut for unknown kinds)."""
    fn = BUILDING_LINES.get(kind)
    if fn:
        return fn(base)
    return [_part("_box(Vector3(1.2, 1.0, 1.2))", _WALL, _at(base, 0, 0.5, 0)),
            _part("_prism(Vector3(1.4, 0.7, 1.3))", _ROOF, _at(base, 0, 1.35, 0))]


# -- goose ----------------------------------------------------------------------------

def goose_lines(base, s: float = 1.0, face: float = -1.0) -> "list[str]":
    """A stylized goose at ``base``, scaled by ``s``, facing -X (face=-1) or +X (face=+1). Body, S-neck,
    head, orange beak, dark eyes with a catch-light, folded wings, upturned tail."""
    def p(dx, dy, dz):
        return _at(base, face * dx * s, dy * s, dz * s)

    def r(rx, ry, rz):
        return (rx, face * ry, face * rz)

    out = [
        _part("_ball(1.0)", _WHITE, p(0, 1.0, 0), (1.7 * s, 1.0 * s, 1.15 * s)),
        _part("_cone(0.32, 0.75)", _WHITE, p(-1.55, 1.4, 0), (s, s, s), r(0, 0, -52)),
        _part("_ball(0.9)", _WINGC, p(-0.15, 1.25, 0.72), (1.5 * s, 0.8 * s, 0.5 * s), r(0, -14, 10)),
        _part("_ball(0.9)", _WINGC, p(-0.15, 1.25, -0.72), (1.5 * s, 0.8 * s, 0.5 * s), r(0, 14, 10)),
    ]
    neck = [(1.2, 1.5, 0, 0.36), (1.4, 1.85, 0, 0.34), (1.55, 2.2, 0, 0.32), (1.62, 2.55, 0, 0.31),
            (1.58, 2.9, 0, 0.30), (1.65, 3.2, 0, 0.29), (1.85, 3.42, 0, 0.28), (2.08, 3.5, 0, 0.27)]
    for nx, ny, nz, nr in neck:
        out.append(_part(f"_ball({nr})", _WHITE, p(nx, ny, nz), (s, s, s)))
    hx, hy, hz = 2.28, 3.55, 0
    out.append(_part("_ball(0.44)", _WHITE, p(hx, hy, hz), (s, s, s)))
    out.append(_part("_cone(0.2, 0.66)", _BEAK, p(hx + 0.54, hy - 0.06, 0), (s, s, s), r(0, 0, 90)))
    out.append(_part("_ball(0.12)", _BEAK, p(hx + 0.28, hy - 0.04, 0), (0.7 * s, 0.9 * s, 1.0 * s)))
    for dz in (0.3, -0.3):
        out.append(_part("_ball(0.08)", _DARK, p(hx + 0.18, hy + 0.15, dz), (s, s, s)))
        out.append(_part("_ball(0.03)", _WHITE, p(hx + 0.32, hy + 0.2, dz), (s, s, s)))
    return out


# -- scene composition ----------------------------------------------------------------

def compose_model_scene(body_lines: "list[str]", *, cam_target=(0, 0.8, 0), cam_size: float = 13.0) -> str:
    """Wrap model ``body_lines`` (which call the model helpers) into a full, lit, renderable scene.gd."""
    tx, ty, tz = cam_target
    header = f'''extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
    cam.look_at(Vector3({tx:g}, {ty:g}, {tz:g}), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = {cam_size:g}
    cam.current = true
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-50, -40, 0)
    sun.light_energy = 1.2
    add_child(sun)
    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-15, 140, 0)
    fill.light_energy = 0.35
    add_child(fill)
    var worldenv := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = {SKY}
    env.ambient_light_color = Color(0.7, 0.75, 0.82)
    env.ambient_light_energy = 0.5
    worldenv.environment = env
    add_child(worldenv)
    build(self)

'''
    body = "func build(root: Node3D) -> void:\n" + "\n".join(body_lines) + "\n"
    return header + MODEL_HELPERS + "\n" + body
