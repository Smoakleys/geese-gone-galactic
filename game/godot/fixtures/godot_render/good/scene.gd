extends Node3D

# Certification GOOD fixture: a camera looking at green terrain WITH a blue pond -> a real multi-element
# render (land + water), so it clears both the green-dominance floor AND the distinct-scene-colours bar
# (a proper scene has more than bare ground; a degenerate all-green render must NOT certify as good).
func _ready() -> void:
	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(6, 6, 6)
	cam.look_at(Vector3.ZERO, Vector3.UP)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 8
	cam.current = true
	_add_plane(Vector2(8, 8), Color("green"), 0.0)
	_add_plane(Vector2(3, 3), Color("blue"), 0.1)   # a pond -> a second distinct scene colour

func _add_plane(size: Vector2, color: Color, y: float) -> void:
	var plane := PlaneMesh.new()
	plane.size = size
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = color
	var mi := MeshInstance3D.new()
	mi.mesh = plane
	mi.material_override = mat
	mi.position = Vector3(0, y, 0)
	add_child(mi)
