# Icarus capability scorecard

North star: Icarus's **UNAIDED** pass rate on novel, procedurally-generated tasks (no notebook, no
best-of-N, ≤1 self-repair). Instances rotate each run (non-memorizable by construction). Updated when
capability moves. Generators + deterministic verifiers live in `harness/icarus/eval/capability.py`.

## Latest — 2026-07-02 (logic: gpt-oss:20b · visuals: qwen3:30b via routing)

**Unaided logic battery: 5/6 = 0.83** (clean run, single model, no GPU contention)

| Domain | Task | Result |
|---|---|---|
| coding | arithmetic (sum) | PASS |
| coding | **debugging** (fix a broken file) | **FAIL** ← standing weakness |
| game-logic | bread economy | PASS |
| game-logic | building placement | PASS |
| game-logic | pond-tick (placement + economy wired) | PASS |
| game-logic | water access (spatial reach) | PASS |

**One Pond game-logic: 4/4 unaided** — every pond mechanic passed.
**Visuals (routed to qwen3:30b): 3/3** on render — Icarus builds land+water+building scenes that clear
the certified `godot_parse` + `godot_render` gates (see `game/godot/scenes/one_pond.gd`).

## Honest reading
Icarus writes fresh logic well — all four One Pond mechanics unaided — and, via model routing, builds
the game's visuals. Its **standing weakness is debugging existing broken code**.

**Debugging characterization (2026-07-03): 2/4, and it's GENERAL** — fails on both bug-types
(wrong-operator `fix_bug` AND off-by-one `fix_range_bug`), ~50%. Diagnosed by looking at a failed
workspace: **the file is left completely unedited** (`print(31 - 63)` still there). So the failure mode
is not *mis*-fixing — it's **finishing without applying the fix at all**: Icarus reads the broken file,
"understands" it, and calls `finish` without ever writing the corrected file or running to confirm.

**The lever this points at:** a *verify-before-finish* discipline — Icarus should not `finish` a fix-it
task without having made an edit and run the file to confirm the output changed. Candidate implementations
(each needs a measured before→after per the plan): a short "run to confirm before finishing" nudge; or a
runtime guard that questions a `finish` when no `write_file`/`run` happened this task. Deferred to a
focused measured cycle so a prompt change isn't kept unless the unaided score actually rises.

## Caveat
An earlier routed full-battery run measured 4/6, but it was the victim of GPU contention (two 30B tasks
overlapping — 31 min; the empty-output failures were starvation artifacts). Trust clean single-model
runs like the one above, not contended ones (see the single-live-run note in `docs/HANDOFF.md`).

## Method
Each generator ships its own deterministic checker; scored UNAIDED (the honest north star). Assisted
(notebook) and routed full-battery runs are also available via `run_battery(..., router=...)`.
