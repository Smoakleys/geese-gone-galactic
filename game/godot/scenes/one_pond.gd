# The canonical One Pond scene — green land + a blue water pond + a building.
# BUILT BY ICARUS (the local agent, routed to qwen3:30b) and kept here as the game's first real scene
# asset + a regression fixture: tests/test_godot_checks.py holds it to the certified godot_parse +
# godot_render gates, so the reference scene can never silently rot. Preserved as the agent produced it.
extends Node3D

func _ready():
    # Camera setup (must be added to scene before look_at)
    var camera = Camera3D.new()
    add_child(camera)
    camera.current = true
    camera.position = Vector3(10, 10, 10)
    camera.look_at(Vector3.ZERO, Vector3.UP)
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.size = 15

    # Green land plane (unshaded)
    var land = MeshInstance3D.new()
    land.mesh = PlaneMesh.new()
    land.mesh.size = Vector2(16, 16)
    land.position = Vector3(0, 0, 0)
    var land_mat = StandardMaterial3D.new()
    land_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    land_mat.albedo_color = Color.GREEN
    land.material_override = land_mat
    add_child(land)

    # Blue water plane (slightly raised, unshaded)
    var water = MeshInstance3D.new()
    water.mesh = PlaneMesh.new()
    water.mesh.size = Vector2(6, 6)
    water.position = Vector3(0, 0, 0.1)
    var water_mat = StandardMaterial3D.new()
    water_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    water_mat.albedo_color = Color.BLUE
    water.material_override = water_mat
    add_child(water)

    # Brown building (unshaded)
    var building = MeshInstance3D.new()
    building.mesh = BoxMesh.new()
    building.mesh.size = Vector3(2, 2, 3)
    building.position = Vector3(3, 0, 0.1)
    var build_mat = StandardMaterial3D.new()
    build_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    build_mat.albedo_color = Color.BROWN
    building.material_override = build_mat
    add_child(building)
