extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(14, 12, 14)
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
    var g := PlaneMesh.new()
    g.size = Vector2(16, 16)
    _part(root, g, Color(0.42, 0.62, 0.32), Vector3(0, 0, 0))
    var pd := PlaneMesh.new()
    pd.size = Vector2(6, 6)
    _part(root, pd, Color(0.28, 0.52, 0.72), Vector3(0, 0.02, 0))
    _part(root, _ball(1.0), Color(0.97, 0.97, 0.94), Vector3(0, 1, 0), Vector3(1.7, 1, 1.15), Vector3(0, 0, 0))
    _part(root, _cone(0.32, 0.75), Color(0.97, 0.97, 0.94), Vector3(1.55, 1.4, 0), Vector3(1, 1, 1), Vector3(0, 0, 52))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(0.15, 1.25, 0.72), Vector3(1.5, 0.8, 0.5), Vector3(0, 14, -10))
    _part(root, _ball(0.9), Color(0.88, 0.88, 0.85), Vector3(0.15, 1.25, -0.72), Vector3(1.5, 0.8, 0.5), Vector3(0, -14, -10))
    _part(root, _ball(0.400), Color(0.97, 0.97, 0.94), Vector3(-1.2, 1.5, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.394), Color(0.97, 0.97, 0.94), Vector3(-1.26667, 1.61667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.388), Color(0.97, 0.97, 0.94), Vector3(-1.33333, 1.73333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.381), Color(0.97, 0.97, 0.94), Vector3(-1.4, 1.85, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.375), Color(0.97, 0.97, 0.94), Vector3(-1.45, 1.96667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.369), Color(0.97, 0.97, 0.94), Vector3(-1.5, 2.08333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.363), Color(0.97, 0.97, 0.94), Vector3(-1.55, 2.2, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.357), Color(0.97, 0.97, 0.94), Vector3(-1.57333, 2.31667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.350), Color(0.97, 0.97, 0.94), Vector3(-1.59667, 2.43333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.344), Color(0.97, 0.97, 0.94), Vector3(-1.62, 2.55, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.338), Color(0.97, 0.97, 0.94), Vector3(-1.60667, 2.66667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.332), Color(0.97, 0.97, 0.94), Vector3(-1.59333, 2.78333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.326), Color(0.97, 0.97, 0.94), Vector3(-1.58, 2.9, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.320), Color(0.97, 0.97, 0.94), Vector3(-1.60333, 3, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.313), Color(0.97, 0.97, 0.94), Vector3(-1.62667, 3.1, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.307), Color(0.97, 0.97, 0.94), Vector3(-1.65, 3.2, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.301), Color(0.97, 0.97, 0.94), Vector3(-1.71667, 3.27333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.295), Color(0.97, 0.97, 0.94), Vector3(-1.78333, 3.34667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.289), Color(0.97, 0.97, 0.94), Vector3(-1.85, 3.42, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.282), Color(0.97, 0.97, 0.94), Vector3(-1.92667, 3.44667, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.276), Color(0.97, 0.97, 0.94), Vector3(-2.00333, 3.47333, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.270), Color(0.97, 0.97, 0.94), Vector3(-2.08, 3.5, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.44), Color(0.97, 0.97, 0.94), Vector3(-2.28, 3.55, 0), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _cone(0.2, 0.66), Color(0.96, 0.55, 0.08), Vector3(-2.82, 3.49, 0), Vector3(1, 1, 1), Vector3(0, 0, -90))
    _part(root, _ball(0.12), Color(0.96, 0.55, 0.08), Vector3(-2.56, 3.51, 0), Vector3(0.7, 0.9, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-2.46, 3.7, 0.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-2.6, 3.75, 0.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.08), Color(0.05, 0.05, 0.05), Vector3(-2.46, 3.7, -0.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
    _part(root, _ball(0.03), Color(0.97, 0.97, 0.94), Vector3(-2.6, 3.75, -0.3), Vector3(1, 1, 1), Vector3(0, 0, 0))
