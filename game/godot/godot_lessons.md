# Icarus's Godot lessons (durable, curated notebook)

General Godot 4 domain knowledge distilled from diagnosed failures — patterns that turn a
syntactically-valid but EMPTY render into a visible scene. These are general rules, not per-ticket
answers, and this file is the CURATED seed: live runs append to a working copy, and only reviewed
lessons are promoted back here (so it never fills with a struggling model's confused scratch notes).

- Godot: call `look_at()` only AFTER `add_child()` — `look_at` errors if the node is not yet in the
  scene tree, so the camera keeps its default orientation and the render shows only the empty gray
  background. This is the #1 cause of an empty render.
- Godot Camera3D orthographic size is the property `size` (not `orthogonal_size`).
- Godot Camera3D orthographic projection is `cam.projection = Camera3D.PROJECTION_ORTHOGONAL`.
- Make the camera active: set `current = true` or call `make_current()` — otherwise nothing you set
  on it is used.
- To FRAME a ground plane in an orthographic camera: put the camera above and to the side (e.g.
  `Vector3(10, 10, 10)`), `look_at(Vector3.ZERO, Vector3.UP)`, and set the ortho `size` to roughly the
  plane's width (e.g. `size` ~= 12-20 for a ~16-unit plane). Too large a `size` makes the plane a tiny
  dot; too small clips into it — either way the frame is mostly empty background.
- For a colour that shows without a light, use a `StandardMaterial3D` with
  `shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED` and set `material_override` on the MeshInstance3D.
- Godot 4 named colours are UPPERCASE constants: `Color.GREEN`, `Color.BLUE`, `Color.GRAY` (NOT the
  Godot-3 lowercase `Color.green`). Lowercase errors at runtime, aborts `_ready()` before the scene is
  built, and the render is empty gray. (Diagnosed from a real blank OP-1 scene.)
- Godot 4 uses `BoxMesh` for a cube — there is NO `CubeMesh` (that was Godot 3). `CubeMesh.new()` errors
  at runtime and blanks the render. Use `var m := BoxMesh.new(); m.size = Vector3(...)`.
- Verify by rendering: if the render is a uniform gray (the default background) the camera saw nothing —
  re-check the camera is current, added to the tree before `look_at`, and framing the object.
