extends Node3D
## A tiny known-good scene to prove the capture rig: an isometric orthographic
## camera looking at a flat green (unshaded, so it needs no lighting) ground plane.

func _ready() -> void:
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 12.0
	cam.position = Vector3(10, 10, 10)
	cam.current = true
	add_child(cam)
	# look_at requires the node to be inside the tree, so aim AFTER add_child.
	cam.look_at(Vector3.ZERO, Vector3.UP)

	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(16, 16)
	ground.mesh = plane
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.3, 0.7, 0.3)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ground.material_override = mat
	add_child(ground)
