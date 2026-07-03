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
task without having made an edit and run the file to confirm the output changed.

**Measured attempt (2026-07-03) — TRIED AND REVERTED.** Implemented exactly that: a runtime guard that
pushes back once on a `finish` when no `write_file`/`run` happened this task. Measured on the same 4
debugging seeds: **2/4 → 2/4 — no rise**, and it caused a *regression* (a previously-passing off-by-one
flipped to FAIL — the nudge made Icarus over-edit into a new bug). Per the plan's rule (keep only if the
unaided score rises), it was **reverted**. Honest conclusion: a simple nudge does not lift gpt-oss:20b's
debugging.

**CONFIRMED + IMPLEMENTED (2026-07-03) — the real lever is model size.** Measured qwen3:30b on the same
4 debugging seeds: **4/4** (vs gpt-oss:20b 2/4). Model SIZE fixes debugging, exactly as it fixed visuals.
Implemented in `visual_router` (harness-mod-35): fix-it/debug tickets now route to the 30B. So **debugging
is no longer a standing weakness when the ticket is routed** — unaided 2/4 → 4/4 on that route, kept per
the plan. Net picture: the fast model handles fresh logic quickly; the 30B handles the harder
visual + debugging work; the router picks per ticket.

## Finding — the StubReviewer's blind spot (2026-07-03)
OP-6 (`pond_scene.py`, a state→GDScript bridge) exposed why a real Stage-B reviewer is the top harness
gap. Icarus's output was almost right — correct add_box lines, colours, positions — but joined them with
`"\\n"` (a LITERAL backslash-n) instead of `"\n"`, so the composed scene is one broken line → blank
render. Stage A (python_syntax) passed (valid Python) and the **StubReviewer** used in the live demos
auto-passed Stage B, so the bug would have committed. A behavioural acceptance check (run `build_body`,
assert real newlines + one line per building) OR a genuine LLM Stage-B reviewer catches this. **This is
the #1 next harness lever** (see ops/backlog.md) — the deterministic gates and the fast build loop are
solid, but subjective correctness currently rides on a stub in unattended runs. The buggy module was NOT
committed.

**RESOLVED (2026-07-03): a local reviewer catches it.** Built `OllamaChatClient` (harness-mod-43) — a
local Stage-B reviewer behind the ChatClient seam, default-FAIL + fail-closed. Ran it on the buggy
`pond_scene.py`: **gpt-oss:20b FAILed it in 4s** (flagged the backslash-n join) and qwen3:30b agreed. A
real subjective reviewer now runs LOCALLY, unattended, no cloud key, and catches subtle behavioural bugs
the StubReviewer waved through. Wired as `default_reviewer()`.

**Recurring lesson (OP-6, then OP-8): a reviewer only enforces what the criterion PINS.** OP-8's
`tick_bread` had the right formula but matched `'baker'` instead of `'bakery'` (counts 0 bakeries →
wrong). The real reviewer, judging against "counts kinds and returns bakeries*(3+granaries) - nests",
passed it — the formula matched; the exact-string typo wasn't in scope. Fix each time: PIN the criterion
(exact strings + a concrete input→output example, e.g. `tick_bread([...]) == 7`). The durable lever for
this class (exact-output logic) is a **deterministic behavioural check** that runs the function against
examples — more reliable than subjective review for typos. Deferred as a focused harness cycle; buggy
modules are NOT committed.

## Caveat
An earlier routed full-battery run measured 4/6, but it was the victim of GPU contention (two 30B tasks
overlapping — 31 min; the empty-output failures were starvation artifacts). Trust clean single-model
runs like the one above, not contended ones (see the single-live-run note in `docs/HANDOFF.md`).

## Method
Each generator ships its own deterministic checker; scored UNAIDED (the honest north star). Assisted
(notebook) and routed full-battery runs are also available via `run_battery(..., router=...)`.
