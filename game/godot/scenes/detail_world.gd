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

func build(root: Node3D) -> void:
    # Ground plane
    add_plane(root, Vector2(16, 16), Color.GREEN)
    
    # Pond
    add_plane(root, Vector2(6, 6), Color.BLUE, 0.1)
    
    # Bakery box (brown)
    add_box(root, Vector3(1.5, 1.5, 1.5), Color(0.5, 0.3, 0.1), Vector3(5, 0.75, 5))
    
    # Nest box (tan)
    add_box(root, Vector3(1, 0.6, 1), Color(0.8, 0.7, 0.4), Vector3(-5, 0.3, 5))
    
    # Goose body
    add_sphere(root, 0.8, Color.WHITE, Vector3(-2, 0.8, -2))
    
    # Neck (two spheres)
    add_sphere(root, 0.3, Color.WHITE, Vector3(-1.7, 1.0, -1.5))
    add_sphere(root, 0.3, Color.WHITE, Vector3(-1.4, 1.2, -1.2))
    
    # Head
    add_sphere(root, 0.4, Color.WHITE, Vector3(-1.1, 1.3, -0.9))
    
    # Beak (orange box)
    add_box(root, Vector3(0.2, 0.2, 0.2), Color(1, 0.5, 0), Vector3(-0.9, 1.4, -0.8))
    
    # Tail (white box)
    add_box(root, Vector3(0.3, 0.1, 0.6), Color.WHITE, Vector3(-2.5, 0.7, -2))
