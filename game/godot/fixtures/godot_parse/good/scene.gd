extends Node3D
## Valid GDScript fixture — must PASS godot --check-only.

func _ready() -> void:
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 12.0
	add_child(cam)
	print("ready")
