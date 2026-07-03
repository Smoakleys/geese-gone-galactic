# game/pond — the real One Pond game core (Pond era)

The actual Pond-era game logic, **built by Icarus** (the local agent) through the harness, one authored
ticket per module (see `game/onepond_tickets.py`). Every module here was gated by certified deterministic
checks (`python_syntax`, `python_behavior` — exact-output examples) *and* a real local Stage-B reviewer,
then verified and behaviour-locked by a test before commit. This is NOT the legacy `game/onepond` python
toy (that's superseded).

## Modules
| Module | Ticket | What it does |
|---|---|---|
| `bread_tick.py` | OP-2 | `tick(state)` — advance the base bread economy one tick (bakery +, goose −, clamp 0) |
| `placement.py` | OP-3 | `is_valid(cells, n)` — a layout is in-bounds and non-overlapping on the n×n grid |
| `pond_state.py` | OP-4 | `step(state)` (tick with **granary synergy**: bakery × (3+granaries) − nests) + `add_building(...)` validated placement |
| `predator.py` | OP-5 | `is_safe(nests, fences, reach)` — every nest within Manhattan `reach` of a fence |
| `granary.py` | OP-7 | `production(bakeries, granaries)` — `bakeries × (3 + granaries)` (each granary boosts every bakery) |
| `pond_economy.py` | OP-8 | `tick_bread(buildings)` — net bread/tick over a building list, using the granary synergy |
| `pond_scene.py` | OP-6 | `build_body(buildings)` — GDScript `add_box` lines (colour + grid position) per building; the state→scene bridge |
| `pond_status.py` | OP-9 | `pond_status(state, reach)` — `{'bread', 'safe'}`, composing predator safety over the state |
| `pond_outcome.py` | OP-10 | `pond_outcome(state, reach)` — `'lost'` (no bread) / `'dry'` (a bakery with no well) / `'unsafe'` (an exposed nest) / `'thriving'`; the layered win/lose evaluation |
| `water_access.py` | OP-11 | `has_water(buildings, reach)` — every bakery must be within `reach` of a well |
| `pond_score.py` | OP-12 | `pond_score(state)` — bread + weighted building values (bakery 10, granary 5, nest 3, else 2) |
| `pond_advice.py` | OP-13 | `pond_advice(state, reach)` — the hint system: suggests the next build by the weakest point |
| `predator_loss.py` | OP-14 | `predator_loss(state, reach)` — bread eaten this tick (2 per unguarded nest); predators with teeth |
| `build_cost.py` | OP-15 | `total_cost(buildings)` — bread cost to place a layout (bakery 5, granary 4, well 3, fence 2, nest 1); scarcity |

## How they compose — the full economic loop
A pond is a `state = {'bread': int, 'buildings': [{'kind','x','y'}, ...]}`. The loop: **spend** bread to
build (`build_cost.total_cost`) on a `placement`-validated layout that needs `water_access`; **earn** it
back as `step` advances the granary-synergy economy; **lose** it to predators (`predator_loss`) when nests
are unguarded. `pond_status`/`pond_outcome`/`pond_score` read the health, `pond_advice` suggests the next
build, and `pond_scene.build_body` (wrapped by `game/godot/scene_template.py`) renders the state to a Godot
scene. `tests/test_one_pond_integration.py` drives the whole loop; `ops/play_onepond.py` plays it end to end.

## Adding a mechanic
Author a ticket in `game/onepond_tickets.py` with PINNED acceptance criteria (exact strings) and
`behavior` examples (`{module, call, expect}` — the deterministic gate). Build it through
`default_icarus_builder` + `default_reviewer` + the full registry; verify the module before committing it
here (the working safety net). Spec-driven: the behavioural check FORCES the pinned contract before commit.
