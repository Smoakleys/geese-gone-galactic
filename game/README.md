# game/ — Geese Gone Galactic (Phase 4: "One Pond")

The game exists to prove the harness works end-to-end. "One Pond" is the smallest complete
slice: a fixed isometric pond, three low-poly buildings (bakery / hatchery / granary), a bread
economy that ticks, and place-a-building + save.

## Authoritative model is Python (so the harness can gate it)

`game/onepond/` holds the **authoritative** game logic in pure Python:

| Module | Role |
|---|---|
| `world.py` | World state, the three buildings, the bread-economy `tick`, placement rules, save/load, `simulate_solvency` |
| `checks.py` | Stage-A game checks: `onepond_placement_valid`, `onepond_economy_solvent` (+ `build_onepond_registry`) |
| `tickets.py` | The One Pond ticket set (frozen criteria) + the Icarus generation client |
| `render.py` | Screenshot seam: `StubScreenshotWorker` (Pillow, now) / `GodotXvfbWorker` (real, drop-in) |
| `iso_camera.json` | The fixed isometric camera — constant so the visual gate compares like-for-like |
| `rubric.md` | Stage-B rubric |

Keeping the logic in Python means the bread economy, placement, and save are built, gated, and
regression-tested by the harness with **no Godot binary required**. GDScript is a thin view.

## Godot / screenshot seam (the remaining external dependency)

Godot `--headless` disables rendering, so real screenshots need Godot under a virtual
framebuffer (Xvfb). That is isolated behind `render.ScreenshotWorker`:

- **Today:** `StubScreenshotWorker` renders a config top-down with Pillow, and the same
  `ReferenceAnchoredScorer` used in Stage B scores it — so "the visual gate sees the game" is
  already true and tested.
- **Drop-in:** `GodotXvfbWorker` launches the Godot project under `xvfb-run` at
  `iso_camera.json` and grabs the framebuffer. When a Godot binary + Xvfb are available, swap
  the worker; nothing else changes.

## How the harness builds One Pond

`build_onepond_registry` (default checks + game checks) + `control.AutonomousRunner` +
`LLMBuilder(onepond_generation_client())` drives `onepond_tickets()` through the strict loop.
Each ticket's `onepond_config.json` must clear Stage A (legal + solvent + valid JSON) and Stage
B before the Gatekeeper commits it to `game/accepted/`. See `tests/test_phase4_onepond.py` for
the end-to-end run and the autonomy-rate assertion.
