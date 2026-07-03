# game/godot/scenes — the visual One Pond (built by Icarus)

Godot 4 (GDScript) scenes, **built by the local agent** through the render path: for each scene ticket
Icarus writes only `func build(root)` calling the tolerant `add_plane` / `add_box` / `add_sphere` helpers
(sphere = rounded shapes, e.g. a less-blocky goose body/head); the scene
template (`game/godot/scene_template.py`) wraps it with a fixed iso camera into a full `scene.gd`; and it
must clear the certified `godot_parse` + `godot_render` gates plus the Stage-B reviewer before commit.
Every scene here is regression-locked in `tests/test_godot_checks.py`. Render offscreen with
`game/godot/capture.py`.

## Scenes
| Scene | Ticket | What it shows |
|---|---|---|
| `one_pond.gd` | OP-1 | The base pond: green land + a blue pond + a building |
| `one_pond_full.gd` | OP-6 (regen) | The full state: land + water + 5 coloured building types, composed from `pond_scene.build_body` over a layout |
| `goose_pond.gd` | OP-24 | A goose beside the pond — the game's namesake (white body + head + orange beak) |
| `flock_pond.gd` | OP-25 | A flock of three geese by the pond |
| `world_pond.gd` | OP-26 | The COMPLETE world: pond + bakery + nest + two geese (box-era) |
| `detail_goose_pond.gd` | OP-34 | A more detailed goose (sphere body + curved neck + head + beak + tail) |
| `detail_world.gd` | OP-35 | **Hero image**: the full lit world — pond + bakery + nest + a detailed goose |

## The visual push
The game grew logic-first (28 `game/pond` modules); the visuals were then deliberately deepened: base →
full-buildings → goose → flock → complete world → **a more detailed goose → LIGHTING**. The template now
adds a sun + soft ambient and uses lit (not unshaded) materials, so spheres show gradients and boxes show
face-shading — 3D depth instead of flat clip-art (all scenes re-lit; `one_pond.gd` stays flat, older
format). Honest ceiling: primitives + lighting is as far as this goes; genuinely goose-*shaped* art needs
real 3D models (see memory `ggg-abstract-visuals-fail-judges`). The low-poly, iso, fixed-camera style keeps
scenes buildable by the fast resident model (~19s) rather than the offloaded 30B (see `docs/SPEED.md`).

## Adding a scene
Author a templated scene ticket in `game/onepond_tickets.py` (kind SYSTEM, Stage-A hints `godot_parse` +
`godot_render`, a Stage-B `rubric_ref`; NO `behavior` — scenes are gated visually, not by exact output).
Build via `default_icarus_builder` (its `post_build` materialises `content.gd` → `scene.gd`) with a
registry that includes the Godot checks. Position meshes via the helper `pos`/`y` ARGS (the helpers return
the node too, but use `.position`, not the Godot-3 `.translation`). LOOK at the actual render before
committing — the metrics are a guardrail, not the judgement. `godot_render` now fails a degenerate
land-only render (< 3 distinct colours) AND a scene that crashed mid-`_ready()` (a logged `SCRIPT ERROR`
still emits a partial frame) — both real gaps found + closed while building these scenes.
