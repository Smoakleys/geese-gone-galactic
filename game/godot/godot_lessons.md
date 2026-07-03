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
- A `PlaneMesh` is ALREADY flat in the horizontal XZ plane. Do NOT `rotate_x(-90°)` it — that stands it
  up VERTICAL, so a top-down/iso camera sees it edge-on (an invisible thin line) and the ground/pond
  vanish. Add planes with no rotation; only raise the pond slightly on Y to layer it over the grass.
- GDScript has NO keyword arguments. Call functions positionally: `add_plane(root, size, color, 0.1)`,
  NOT `add_plane(root, size, color, y=0.1)` — a `name=` argument is a parse error.
- Node3D position is `node.position` (Godot 4), NOT `node.translation` (that was Godot 3) — `translation`
  errors at runtime and blanks the scene.
- If helper functions are already defined in the SAME script, just call them directly
  (`add_plane(...)`); do NOT `preload("res://helpers.gd")` or prefix them (`helpers.add_plane`) — the
  file has no such separate resource, so that errors.
- Verify by rendering: if the render is a uniform gray (the default background) the camera saw nothing —
  re-check the camera is current, added to the tree before `look_at`, and framing the object.

## Building GOOD-looking scenes — use the one-call PROP helpers (don't hand-place blobs)

The scene template gives you high-level helpers that build a whole MODELLED prop in one call. PREFER these
over stacking raw spheres/boxes yourself — they already look like real geese and buildings (a body of
primitives placed by an artist's hand), so your scene reads as a cozy village, not cubes:
- `add_building(root, "bakery"|"granary"|"nest"|"well"|"fence", Vector3(x, 0, z))` — a modelled building
  (roofed house, silo, nest+eggs, roofed well, fence). There are also direct `add_bakery(root, pos)` etc.
- `add_goose(root, Vector3(x, 0, z), s, f)` — a stylized goose: `s` scales it (0.4–0.5 for a goose in a
  pond scene, 1.0 for a hero close-up), `f` is facing (-1.0 faces -X, 1.0 faces +X). Put a goose beside a
  nest or on the pond.
- A good pond scene: `add_plane(root, Vector2(20,20), Color(0.42,0.62,0.32))` grass +
  `add_plane(root, Vector2(7,7), Color(0.28,0.52,0.72), 0.02)` pond, then a few `add_building(...)` spread
  ~3 units apart so they don't overlap, and an `add_goose(...)` by each nest. Frame with ortho `size`
  ~12–16 so the props are big enough to see (a huge size makes them tiny dots).
- Palette: soft muted colours read better than pure primaries — grass `Color(0.42,0.62,0.32)`, pond
  `Color(0.28,0.52,0.72)`, not `Color.GREEN`/`Color.BLUE`.
- These helpers use lit materials (there is a sun + ambient), so do NOT set unshaded — the shading is what
  gives the low-poly shapes their 3D depth.
