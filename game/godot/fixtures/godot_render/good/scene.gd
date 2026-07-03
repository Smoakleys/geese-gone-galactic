extends Node3D

# Certification GOOD fixture: a camera looking at a green plane -> renders visible green terrain.
func _ready() -> void:
	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(6, 6, 6)
	cam.look_at(Vector3.ZERO, Vector3.UP)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 8
	cam.current = true
	var plane := PlaneMesh.new()
	plane.size = Vector2(8, 8)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color("green")
	var mi := MeshInstance3D.new()
	mi.mesh = plane
	mi.material_override = mat
	add_child(mi)
