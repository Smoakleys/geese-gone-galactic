extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
    cam.look_at(Vector3(0, 0.7, 0), Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 11
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
    grass.size = Vector2(18, 18)
    _part(root, grass, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pond := PlaneMesh.new()
    pond.size = Vector2(7, 7)
    _part(root, pond, Color(0.28, 0.52, 0.72), Vector3(0, 0.02, 0))
    _part(root, _box(Vector3(1.6, 1.2, 1.4)), Color(0.93, 0.85, 0.62), Vector3(-3, 0.6, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _prism(Vector3(1.9, 0.95, 1.6)), Color(0.72, 0.26, 0.2), Vector3(-3, 1.68, -3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.25, 0.55, 0.25)), Color(0.62, 0.62, 0.6), Vector3(-2.5, 1.9, -3.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _box(Vector3(0.45, 0.65, 0.06)), Color(0.55, 0.36, 0.22), Vector3(-3, 0.33, -2.29), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(2, 0.55, 1), Vector3(0.935, 0.55, 0.6325), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(2.8525, 0.77, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(2.0825, 0.6875, 1.396), Vector3(0.825, 0.44, 0.275), Vector3(0, 14, -10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(2.0825, 0.6875, 0.604), Vector3(0.825, 0.44, 0.275), Vector3(0, -14, -10))
    _part(root, _ball(0.36), Color(0.97, 0.97, 0.94), Vector3(1.34, 0.825, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.34), Color(0.97, 0.97, 0.94), Vector3(1.23, 1.0175, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.32), Color(0.97, 0.97, 0.94), Vector3(1.1475, 1.21, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.31), Color(0.97, 0.97, 0.94), Vector3(1.109, 1.4025, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.3), Color(0.97, 0.97, 0.94), Vector3(1.131, 1.595, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.29), Color(0.97, 0.97, 0.94), Vector3(1.0925, 1.76, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.28), Color(0.97, 0.97, 0.94), Vector3(0.9825, 1.881, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.27), Color(0.97, 0.97, 0.94), Vector3(0.856, 1.925, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(0.746, 1.9525, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(0.449, 1.9195, 1), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, -90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(0.592, 1.9305, 1), Vector3(0.385, 0.495, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.647, 2.035, 1.165), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.57, 2.0625, 1.165), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(0.647, 2.035, 0.835), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(0.57, 2.0625, 0.835), Vector3(0.55, 0.55, 0.55), Vector3(0, 0, 0))
