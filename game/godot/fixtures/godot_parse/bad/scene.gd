extends Node3D
## Broken GDScript fixture — MUST FAIL godot --check-only (missing colon after the signature).

func _ready() -> void
	print("this will not parse")
