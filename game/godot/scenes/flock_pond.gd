extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
    cam.look_at(Vector3(0, 0.7, 0), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 15
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
    grass.size = Vector2(22, 22)
    _part(root, grass, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pond := PlaneMesh.new()
    pond.size = Vector2(10, 8)
    _part(root, pond, Color(0.28, 0.52, 0.72), Vector3(0, 0.02, 0))
    _part(root, _box(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), Vector3(-4, 0.6, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), Vector3(-4, 1.68, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), Vector3(-3.5, 1.9, -4.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), Vector3(-4, 0.33, -3.29), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.75, 1.7), Color(0.85, 0.7, 0.45), Vector3(3, 0.85, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cone(0.95, 0.8), Color(0.72, 0.26, 0.2), Vector3(3, 2.1, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cyl(0.78, 0.12), Color(0.55, 0.36, 0.22), Vector3(3, 1.2, -4), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(-1, 0.5, 1), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-1.775, 0.7, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-1.075, 0.625, 1.36), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-1.075, 0.625, 0.64), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(-0.4, 0.75, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(-0.3, 0.925, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(-0.225, 1.1, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(-0.19, 1.275, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(-0.21, 1.45, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(-0.175, 1.6, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(-0.075, 1.71, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(0.04, 1.75, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(0.14, 1.775, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(0.41, 1.745, 1), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(0.28, 1.755, 1), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.23, 1.85, 1.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.3, 1.875, 1.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.23, 1.85, 0.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.3, 1.875, 0.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(1.5, 0.5, 2), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(2.275, 0.7, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(1.575, 0.625, 2.36), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, -10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(1.575, 0.625, 1.64), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, -10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(0.9, 0.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(0.8, 0.925, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(0.725, 1.1, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(0.69, 1.275, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(0.71, 1.45, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(0.675, 1.6, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(0.575, 1.71, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(0.46, 1.75, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(0.36, 1.775, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(0.09, 1.745, 2), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(0.22, 1.755, 2), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.27, 1.85, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.2, 1.875, 2.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.27, 1.85, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.2, 1.875, 1.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(-2.5, 0.5, 3), Vector3(0.85, 0.5, 0.575), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(-3.275, 0.7, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, -52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-2.575, 0.625, 3.36), Vector3(0.75, 0.4, 0.25), Vector3(0, -14, 10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(-2.575, 0.625, 2.64), Vector3(0.75, 0.4, 0.25), Vector3(0, 14, 10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(-1.9, 0.75, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(-1.8, 0.925, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(-1.725, 1.1, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(-1.69, 1.275, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(-1.71, 1.45, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(-1.675, 1.6, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(-1.575, 1.71, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(-1.46, 1.75, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(-1.36, 1.775, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(-1.09, 1.745, 3), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(-1.22, 1.755, 3), Vector3(0.35, 0.45, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-1.27, 1.85, 3.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-1.2, 1.875, 3.15), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-1.27, 1.85, 2.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-1.2, 1.875, 2.85), Vector3(0.5, 0.5, 0.5), Vector3(0, 0, 0))
