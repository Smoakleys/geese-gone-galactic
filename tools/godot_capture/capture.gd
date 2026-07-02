extends Node
## GGG capture rig entry point.
## Usage: godot --path tools/godot_capture -- --scene=<res://or abs path> --out=<abs.png> [--size=WxH]
## Loads the target scene into an own-world SubViewport, renders a few frames, saves a PNG, quits.
## Exit codes: 0 ok, 2 bad args, 3 load failed, 4 save failed.

func _ready() -> void:
	var args := _parse_args()
	var scene_path: String = args.get("scene", "")
	var out_path: String = args.get("out", "")
	var size_str: String = args.get("size", "512x512")
	if scene_path == "" or out_path == "":
		push_error("usage: --scene=<path> --out=<png> [--size=WxH]")
		get_tree().quit(2)
		return

	var wh := size_str.split("x")
	var vp_size := Vector2i(int(wh[0]), int(wh[1])) if wh.size() == 2 else Vector2i(512, 512)

	# Shove the real window off-screen so nothing flashes on the desktop (do NOT minimize —
	# minimizing pauses rendering).
	DisplayServer.window_set_position(Vector2i(-4000, -4000))

	var sub := SubViewport.new()
	sub.size = vp_size
	sub.own_world_3d = true
	sub.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(sub)

	var packed: PackedScene = load(scene_path)
	if packed == null:
		push_error("failed to load scene: " + scene_path)
		get_tree().quit(3)
		return
	sub.add_child(packed.instantiate())

	# Let the instanced scene's _ready run and the renderer draw a few frames.
	for i in range(4):
		await get_tree().process_frame
	for i in range(3):
		await RenderingServer.frame_post_draw

	var img := sub.get_texture().get_image()
	var err := img.save_png(out_path)
	if err != OK:
		push_error("save_png failed: %d" % err)
		get_tree().quit(4)
		return
	print("captured %s -> %s (%dx%d)" % [scene_path, out_path, vp_size.x, vp_size.y])
	get_tree().quit(0)


func _parse_args() -> Dictionary:
	var out := {}
	for a in OS.get_cmdline_user_args():
		var s := String(a)
		if s.begins_with("--"):
			s = s.substr(2)
		var eq := s.find("=")
		if eq > 0:
			out[s.substr(0, eq)] = s.substr(eq + 1)
	return out
