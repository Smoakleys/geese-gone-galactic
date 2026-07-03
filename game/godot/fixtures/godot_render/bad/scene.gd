extends Node3D

# Certification BAD fixture: a valid script (parses fine) with a camera but NO scene content -> the
# camera sees only the empty grey background, so the render is blank. Parses, but must FAIL the render gate.
func _ready() -> void:
	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(6, 6, 6)
	cam.look_at(Vector3.ZERO, Vector3.UP)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 8
	cam.current = true
