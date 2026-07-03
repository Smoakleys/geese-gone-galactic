# game/godot/scenes — the visual One Pond (built by Icarus)

Godot 4 (GDScript) scenes rendered through the offscreen path. Each scene writes a `func build(root)` that
calls the scene-template helpers; the template (`game/godot/scene_template.py`) wraps it with a lit iso
camera into a full `scene.gd`; and it must clear the certified `godot_parse` + `godot_render` gates (+ the
Stage-B reviewer) before commit. All are regression-locked in `tests/test_godot_checks.py`. Render offscreen
with `game/godot/capture.py` (8x MSAA + 1024px).

The helpers are one-call PROP builders (backed by `game/godot/models.py`): `add_building(root, kind, pos)`
(kind = bakery/granary/nest/well/fence), `add_goose(root, pos, s, f)`, `add_tree(root, pos, s)`, plus the
low-level `add_plane`/`add_box`/`add_sphere`. So a scene is a few readable calls, and Icarus builds a real
village — not hand-stacked blobs.

## Scenes
| Scene | What it shows |
|---|---|
| `detail_goose_pond.gd` | **Hero goose**: a stylized goose (ellipsoid body, smooth S-neck, cone beak, eyes, folded wings, tail) on a pond — reads as "a swan" to the vision judge |
| `detail_world.gd` | **Hero world**: a cozy village — granary, two roofed bakeries, well, fences, nests, trees, and four geese on the pond |
| `world_pond.gd` | A village: bakery + granary + nest + well + fence + geese |
| `goose_pond.gd` | A goose beside a bakery by the pond |
| `flock_pond.gd` | A flock of geese with a couple of buildings |
| `detail_flock.gd` | A five-goose flock on the pond |
| `one_pond.gd` / `one_pond_full.gd` | The original base scenes (older box format; `one_pond` is the canonical regression fixture referenced by many tests) |

## The look (rebuilt 2026-07-03 on Bridger's "these are cubes" feedback)
The visuals were rebuilt from coloured boxes into a cozy low-poly VILLAGE via `game/godot/models.py`:
modelled buildings (gabled `PrismMesh` roofs, cone silo/roofs, nests with eggs), a real goose (smooth
interpolated neck), trees, a soft palette, anti-aliasing + 1024px. **Vision-validated**: the local vision
model (`qwen2.5vl`) reads the village as "swans, nests, trees, houses, water" and the goose as "a swan"
(docs/SCORECARD.md) — SUPERSEDING the old "primitives can't look like geese" note in
`ggg-abstract-visuals-fail-judges` (that was the blob art). The honest lever was real geometry effort, not a
gate hack. The `godot_render` gate uses region green-fraction (not whole-frame mean) so a natural palette
passes while blanks/degenerate renders still fail.

## Adding a scene
Prefer the one-call helpers: grass + pond planes, then `add_building`/`add_goose`/`add_tree` a few units
apart, framed with ortho `size` ~12–18 so props stay a visible fraction (the gate needs >=3 distinct
colours). Build via `default_icarus_builder` (its `post_build` materialises `content.gd` → `scene.gd`) with
a registry including the Godot checks. Use `.position`, NOT the Godot-3 `.translation`. LOOK at the actual
render before committing — the metrics are a guardrail, not the judgement — and, now that props are
recognisable, `game/godot/scene_review.py` can vision-check that a render reads as a pond scene.
