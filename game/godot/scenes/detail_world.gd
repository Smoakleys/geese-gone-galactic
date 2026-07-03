extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
    cam.look_at(Vector3(0, 0.6, 0), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 22
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
    grass.size = Vector2(30, 30)
    _part(root, grass, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pond := PlaneMesh.new()
    pond.size = Vector2(11, 9)
    _part(root, pond, Color(0.28, 0.52, 0.72), Vector3(0.5, 0.02, 1))
    _part(root, _box(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), Vector3(-5.5, 0.6, -4.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), Vector3(-5.5, 1.68, -4.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), Vector3(-5, 1.9, -4.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), Vector3(-5.5, 0.33, -3.79), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), Vector3(-2.5, 0.6, -6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), Vector3(-2.5, 1.68, -6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), Vector3(-2, 1.9, -6.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), Vector3(-2.5, 0.33, -5.29), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.75, 1.7), Color(0.85, 0.7, 0.45), Vector3(-6.5, 0.85, -1.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cone(0.95, 0.8), Color(0.72, 0.26, 0.2), Vector3(-6.5, 2.1, -1.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.78, 0.12), Color(0.55, 0.36, 0.22), Vector3(-6.5, 1.2, -1.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.55, 0.7), Color(0.62, 0.62, 0.6), Vector3(5.5, 0.35, -3.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), Vector3(5.05, 0.9, -3.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.1, 1.0, 0.1)), Color(0.55, 0.36, 0.22), Vector3(5.95, 0.9, -3.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.3, 0.4, 0.9)), Color(0.72, 0.26, 0.2), Vector3(5.5, 1.55, -3.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.7, 0.35), Color(0.55, 0.36, 0.22), Vector3(-5.5, 0.18, 4.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.45, 0.25), Color(0.4, 0.28, 0.16), Vector3(-5.5, 0.32, 4.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(-5.65, 0.42, 4.6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(-5.32, 0.42, 4.45), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.7, 0.35), Color(0.55, 0.36, 0.22), Vector3(5, 0.18, 4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.45, 0.25), Color(0.4, 0.28, 0.16), Vector3(5, 0.32, 4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(4.85, 0.42, 4.1), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.18), Color(0.96, 0.95, 0.9), Vector3(5.18, 0.42, 3.95), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(-0.6, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(0, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(0.6, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(1.4, 0.12, 0.08)), Color(0.55, 0.36, 0.22), Vector3(0, 0.5, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(2.2, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(2.8, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.12, 0.7, 0.12)), Color(0.55, 0.36, 0.22), Vector3(3.4, 0.35, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(1.4, 0.12, 0.08)), Color(0.55, 0.36, 0.22), Vector3(2.8, 0.5, -6.8), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), Vector3(-9, 0.55, -7), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), Vector3(-9, 1.5, -7), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), Vector3(-8.72, 2.05, -6.9), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), Vector3(-9.3, 1.95, -7.1), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), Vector3(8, 0.55, -6.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), Vector3(8, 1.5, -6.5), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), Vector3(8.28, 2.05, -6.4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), Vector3(7.7, 1.95, -6.6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), Vector3(9, 0.605, 5), Vector3(1.1, 1.1, 1.1), Vector3(0, 0, 0))
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), Vector3(9, 1.65, 5), Vector3(1.1, 1.1, 1.1), Vector3(0, 0, 0))
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), Vector3(9.308, 2.255, 5.11), Vector3(1.1, 1.1, 1.1), Vector3(0, 0, 0))
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), Vector3(8.67, 2.145, 4.89), Vector3(1.1, 1.1, 1.1), Vector3(0, 0, 0))
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), Vector3(-9, 0.55, 6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), Vector3(-9, 1.5, 6), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), Vector3(-8.72, 2.05, 6.1), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), Vector3(-9.3, 1.95, 5.9), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.16, 1.1), Color(0.45, 0.31, 0.19), Vector3(0, 0.495, -9), Vector3(0.9, 0.9, 0.9), Vector3(0, 0, 0))
    _part(root, _ball(0.85), Color(0.30, 0.52, 0.26), Vector3(0, 1.35, -9), Vector3(0.9, 0.9, 0.9), Vector3(0, 0, 0))
    _part(root, _ball(0.62), Color(0.34, 0.57, 0.29), Vector3(0.252, 1.845, -8.91), Vector3(0.9, 0.9, 0.9), Vector3(0, 0, 0))
    _part(root, _ball(0.6), Color(0.34, 0.57, 0.29), Vector3(-0.27, 1.755, -9.09), Vector3(0.9, 0.9, 0.9), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(-1, 0.5, 2), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-1.775, 0.7, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-1.075, 0.625, 2.36), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-1.075, 0.625, 1.64), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(-0.4, 0.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(-0.3, 0.925, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(-0.225, 1.1, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(-0.19, 1.275, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(-0.21, 1.45, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(-0.175, 1.6, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(-0.075, 1.71, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(0.04, 1.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(0.14, 1.775, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(0.41, 1.745, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(0.28, 1.755, 2), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.23, 1.85, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.3, 1.875, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.23, 1.85, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.3, 1.875, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(2, 0.5, 3), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(2.775, 0.7, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(2.075, 0.625, 3.36), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, -10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(2.075, 0.625, 2.64), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, -10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(1.4, 0.75, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(1.3, 0.925, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(1.225, 1.1, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(1.19, 1.275, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(1.21, 1.45, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(1.175, 1.6, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(1.075, 1.71, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(0.96, 1.75, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(0.86, 1.775, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(0.59, 1.745, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(0.72, 1.755, 3), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.77, 1.85, 3.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.7, 1.875, 3.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.77, 1.85, 2.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.7, 1.875, 2.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(-4.3, 0.45, 4.5), Vector3(0.765, 0.45, 0.5175), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-4.9975, 0.63, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-4.3675, 0.5625, 4.824), Vector3(0.675, 0.36, 0.225), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-4.3675, 0.5625, 4.176), Vector3(0.675, 0.36, 0.225), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(-3.76, 0.675, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(-3.67, 0.8325, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(-3.6025, 0.99, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(-3.571, 1.1475, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(-3.589, 1.305, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(-3.5575, 1.44, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(-3.4675, 1.539, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(-3.364, 1.575, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(-3.274, 1.5975, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(-3.031, 1.5705, 4.5), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(-3.148, 1.5795, 4.5), Vector3(0.315, 0.405, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-3.193, 1.665, 4.635), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-3.13, 1.6875, 4.635), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-3.193, 1.665, 4.365), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-3.13, 1.6875, 4.365), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(6.2, 0.45, 4), Vector3(0.765, 0.45, 0.5175), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(6.8975, 0.63, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(6.2675, 0.5625, 4.324), Vector3(0.675, 0.36, 0.225), Vector3(0, 14, -10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(6.2675, 0.5625, 3.676), Vector3(0.675, 0.36, 0.225), Vector3(0, -14, -10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(5.66, 0.675, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(5.57, 0.8325, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(5.5025, 0.99, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(5.471, 1.1475, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(5.489, 1.305, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(5.4575, 1.44, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(5.3675, 1.539, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(5.264, 1.575, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(5.174, 1.5975, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(4.931, 1.5705, 4), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, -90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(5.048, 1.5795, 4), Vector3(0.315, 0.405, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(5.093, 1.665, 4.135), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(5.03, 1.6875, 4.135), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(5.093, 1.665, 3.865), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(5.03, 1.6875, 3.865), Vector3(0.45, 0.45, 0.45), Vector3(0, 0, 0))
