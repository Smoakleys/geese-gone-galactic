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
    # Land plane
    add_plane(root, Vector2(16, 16), Color.GREEN)
    
    # Pond
    add_plane(root, Vector2(6, 6), Color.BLUE, 0.1)
    
    # Geese positions (x, z) with a fixed y offset for body height
    var goose_positions = [
        Vector3(-4, 0.35, -4),
        Vector3(-6, 0.35, -2),
        Vector3(-8, 0.35, 0)
    ]
    
    for pos in goose_positions:
        # Body
        add_box(root, Vector3(1, 0.7, 1.6), Color.WHITE, pos)
        
        # Head offset: above front of body (along +z direction)
        var head_offset = Vector3(0, 0, 1.05)  # half depth of body (~0.8) + small gap
        add_box(root, Vector3(0.5, 0.7, 0.5), Color.WHITE, pos + head_offset)
        
        # Beak offset: above front of head (small forward offset)
        var beak_offset = Vector3(0, 0, 1.35)  # slightly ahead of head
        add_box(root, Vector3(0.2, 0.2, 0.4), Color(1, 0.5, 0), pos + beak_offset)
