extends Node3D
# A single detailed goose on a pond -- the reference for what a GGG goose should look like: a plump white
# body, a smooth S-curved neck, an orange beak, a dark eye with a catch-light, folded wings, an upturned
# tail. Built from lit primitives (ellipsoids via scaled spheres + cones), framed tight, natural palette.

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(12, 12, 12)
    cam.look_at(Vector3(-0.3, 1.6, 0), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 8
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
    env.background_color = Color(0.53, 0.81, 0.92)
    env.ambient_light_color = Color(0.7, 0.75, 0.82)
    env.ambient_light_energy = 0.5
    worldenv.environment = env
    add_child(worldenv)
    build(self)


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

func _sphere(r):
    var sm := SphereMesh.new()
    sm.radius = r
    sm.height = r * 2.0
    sm.radial_segments = 40
    sm.rings = 20
    return sm

func _cone(bottom_r, h):
    var cm := CylinderMesh.new()
    cm.top_radius = 0.0
    cm.bottom_radius = bottom_r
    cm.height = h
    cm.radial_segments = 28
    return cm

func build(root):
    var grass := PlaneMesh.new()
    grass.size = Vector2(20, 20)
    _part(root, grass, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pond := PlaneMesh.new()
    pond.size = Vector2(9, 9)
    _part(root, pond, Color(0.28, 0.52, 0.72), Vector3(0, 0.02, 0))

    var white := Color(0.97, 0.97, 0.94)
    var wing := Color(0.88, 0.88, 0.85)
    # BODY
    _part(root, _sphere(1.0), white, Vector3(0, 1.0, 0), Vector3(1.7, 1.0, 1.15))
    # TAIL
    _part(root, _cone(0.32, 0.75), white, Vector3(1.55, 1.4, 0), Vector3.ONE, Vector3(0, 0, -52))
    # WINGS (folded, one per flank)
    _part(root, _sphere(0.9), wing, Vector3(0.15, 1.25, 0.72), Vector3(1.5, 0.8, 0.5), Vector3(0, -14, 10))
    _part(root, _sphere(0.9), wing, Vector3(0.15, 1.25, -0.72), Vector3(1.5, 0.8, 0.5), Vector3(0, 14, 10))
    # NECK (denser tapered spheres -> smooth S-curve)
    var neck_pts := [Vector3(-1.2, 1.5, 0), Vector3(-1.4, 1.85, 0), Vector3(-1.55, 2.2, 0),
                     Vector3(-1.62, 2.55, 0), Vector3(-1.58, 2.9, 0), Vector3(-1.65, 3.2, 0),
                     Vector3(-1.85, 3.42, 0), Vector3(-2.08, 3.5, 0)]
    var neck_r := [0.36, 0.34, 0.32, 0.31, 0.30, 0.29, 0.28, 0.27]
    for i in neck_pts.size():
        _part(root, _sphere(neck_r[i]), white, neck_pts[i])
    # HEAD
    var head := Vector3(-2.28, 3.55, 0)
    _part(root, _sphere(0.44), white, head)
    # BEAK
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), head + Vector3(-0.54, -0.06, 0), Vector3.ONE, Vector3(0, 0, 90))
    _part(root, _sphere(0.12), Color(0.96, 0.6, 0.15), head + Vector3(-0.28, -0.04, 0), Vector3(0.7, 0.9, 1.0))
    # EYES (dark + catch-light)
    for z in [0.3, -0.3]:
        _part(root, _sphere(0.08), Color(0.05, 0.05, 0.05), head + Vector3(-0.18, 0.15, z))
        _part(root, _sphere(0.03), Color.WHITE, head + Vector3(-0.32, 0.2, z))
