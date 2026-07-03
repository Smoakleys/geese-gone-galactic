extends Node3D

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

func build(root: Node3D) -> void:
    # Land plane
    add_plane(root, Vector2(16, 16), Color.GREEN)
    
    # Pond plane slightly above ground
    add_plane(root, Vector2(6, 6), Color.BLUE, 0.1)
    
    # Bakery box (brown)
    add_box(root, Vector3(1.5, 1.5, 1.5), Color(0.5, 0.3, 0.1), Vector3(-4, 0.75, -2))
    
    # Nest box (tan)
    add_box(root, Vector3(1, 0.6, 1), Color(0.8, 0.7, 0.4), Vector3(2, 0.3, 3))
    
    # Goose 1
    var goose1_body_pos = Vector3(5, 0.35, 5)
    add_box(root, Vector3(1, 0.7, 1.6), Color.WHITE, goose1_body_pos)
    var goose1_head_pos = goose1_body_pos + Vector3(-0.25, 0.35, -0.8)
    add_box(root, Vector3(0.5, 0.7, 0.5), Color.WHITE, goose1_head_pos)
    var goose1_beak_pos = goose1_head_pos + Vector3(-0.25, 0.35, -0.4)
    add_box(root, Vector3(0.2, 0.2, 0.4), Color(1, 0.5, 0), goose1_beak_pos)
    
    # Goose 2
    var goose2_body_pos = Vector3(-5, 0.35, -5)
    add_box(root, Vector3(1, 0.7, 1.6), Color.WHITE, goose2_body_pos)
    var goose2_head_pos = goose2_body_pos + Vector3(0.25, 0.35, 0.8)
    add_box(root, Vector3(0.5, 0.7, 0.5), Color.WHITE, goose2_head_pos)
    var goose2_beak_pos = goose2_head_pos + Vector3(0.25, 0.35, 0.4)
    add_box(root, Vector3(0.2, 0.2, 0.4), Color(1, 0.5, 0), goose2_beak_pos)
