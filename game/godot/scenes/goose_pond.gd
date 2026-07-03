extends Node3D

func _ready() -> void:
    var cam := Camera3D.new()
    add_child(cam)
    cam.position = Vector3(12, 12, 12)
    cam.look_at(Vector3.ZERO, Vector3.UP)
    cam.projection = Camera3D.PROJECTION_ORTHOGONAL
    cam.size = 18
    cam.current = true
    build(self)


func _unshaded(color):
    var m := StandardMaterial3D.new()
    m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    m.albedo_color = color
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
    mi.material_override = _unshaded(color)
    root.add_child(mi)

# Helper: add a box (building) of `size` at `pos`.
func add_box(root, size, color, pos = Vector3.ZERO):
    var sz = size if (size is Vector3) else Vector3(float(size), float(size), float(size))
    var mi := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = sz
    mi.mesh = bm
    mi.position = pos
    mi.material_override = _unshaded(color)
    root.add_child(mi)

func build(root: Node3D) -> void:
    # Green land plane
    add_plane(root, Vector2(16, 16), Color.GREEN)
    
    # Blue pond slightly above ground
    add_plane(root, Vector2(6, 6), Color.BLUE, 0.1)
    
    # Goose body (white box)
    var body_pos = Vector3(-4, 0.4, 0)  # positioned beside the pond
    add_box(root, Vector3(1.2, 0.8, 2), Color.WHITE, body_pos)
    
    # Goose head (white box) above front of body
    var head_pos = body_pos + Vector3(0, 0.4, 1)  # slightly higher and forward
    add_box(root, Vector3(0.6, 0.8, 0.6), Color.WHITE, head_pos)
    
    # Goose beak (small orange box) in front of head
    var beak_pos = head_pos + Vector3(0, -0.1, 0.4)  # forward and slightly lower
    add_box(root, Vector3(0.2, 0.2, 0.5), Color(1, 0.5, 0), beak_pos)
