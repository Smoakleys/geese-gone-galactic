extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
    cam.look_at(Vector3(0, 0.6, 0), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 18
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

func build(root: Node3D) -> void:
    var grass := PlaneMesh.new()
    grass.size = Vector2(28, 28)
    _part(root, grass, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pond := PlaneMesh.new()
    pond.size = Vector2(10, 8)
    _part(root, pond, Color(0.28, 0.52, 0.72), Vector3(1, 0.02, 1))
    _part(root, _box(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), Vector3(-5, 0.6, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), Vector3(-5, 1.68, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), Vector3(-4.5, 1.9, -4.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), Vector3(-5, 0.33, -3.29), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.75, 1.7), Color(0.85, 0.7, 0.45), Vector3(-6, 0.85, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cone(0.95, 0.8), Color(0.72, 0.26, 0.2), Vector3(-6, 2.1, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.78, 0.12), Color(0.55, 0.36, 0.22), Vector3(-6, 1.2, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.7, 0.35), Color(0.55, 0.36, 0.22), Vector3(-4, 0.18, 4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.45, 0.25), Color(0.4, 0.28, 0.16), Vector3(-4, 0.32, 4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(-4.15, 0.42, 4.1), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(-3.82, 0.42, 3.95), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.55, 0.7), Color(0.62, 0.62, 0.6), Vector3(5, 0.35, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), Vector3(4.55, 0.9, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), Vector3(5.45, 0.9, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.3, 0.4, 0.9)), Color(0.72, 0.26, 0.2), Vector3(5, 1.55, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(2.4, 0.35, -5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(3, 0.35, -5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(3.6, 0.35, -5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(1.4, 0.12, 0.08)), Color(0.55, 0.36, 0.22), Vector3(3, 0.5, -5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(0, 0.5, 2), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-0.775, 0.7, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-0.075, 0.625, 2.36), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-0.075, 0.625, 1.64), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(0.6, 0.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(0.7, 0.925, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(0.775, 1.1, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(0.81, 1.275, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(0.79, 1.45, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(0.825, 1.6, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(0.925, 1.71, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(1.04, 1.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(1.14, 1.775, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(1.41, 1.745, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(1.28, 1.755, 2), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(1.23, 1.85, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(1.3, 1.875, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(1.23, 1.85, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(1.3, 1.875, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(-2.8, 0.45, 4), Vector3(0.765, 0.45, 0.5175), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-3.4975, 0.63, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-2.8675, 0.5625, 4.324), Vector3(0.675, 0.36, 0.225), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-2.8675, 0.5625, 3.676), Vector3(0.675, 0.36, 0.225), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(-2.26, 0.675, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(-2.17, 0.8325, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(-2.1025, 0.99, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(-2.071, 1.1475, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(-2.089, 1.305, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(-2.0575, 1.44, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(-1.9675, 1.539, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(-1.864, 1.575, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(-1.774, 1.5975, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(-1.531, 1.5705, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(-1.648, 1.5795, 4), Vector3(0.315, 0.405, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-1.693, 1.665, 4.135), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-1.63, 1.6875, 4.135), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-1.693, 1.665, 3.865), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-1.63, 1.6875, 3.865), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
