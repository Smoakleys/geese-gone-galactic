# Icarus capability scorecard

North star: Icarus's **UNAIDED** pass rate on novel, procedurally-generated tasks (no notebook, no
best-of-N, ≤1 self-repair). Instances rotate each run (non-memorizable by construction). Updated when
capability moves. Generators + deterministic verifiers live in `harness/icarus/eval/capability.py`.

## VISUAL validation — the new models PASS an independent vision judge (2026-07-03)
After Bridger's "these are cubes + a pixelly goose" feedback, the visuals were rebuilt as real modelled
props (`game/godot/models.py`: roofed buildings + a stylized goose) with AA + 1024px + a soft palette
(PRs #329-340). Measured OBJECTIVELY with the local vision model `qwen2.5vl:7b` on the renders (the plan's
see-screenshot judge) — the honest test the OLD blob art FAILED (it saw "a green square with a blue square
and an orange shape", see memory ggg-abstract-visuals-fail-judges):
- **Village scene** → *"a serene rural scene with swans, nests, trees, houses, and a small water body
  surrounded by greenery"* — every element recognised.
- **Hero goose** (after smoothing the neck from beads to an interpolated tube, harness/visual iteration) →
  *"This is a swan."* (The beaded-neck version read as "a white snake-like creature" — acted on that
  feedback rather than moving on.)
This is the plan's "gym, not cheat sheet" done honestly on visuals: the model, not the gate, was fixed.
A subjective vision-on-render scene gate is now viable (props are recognisable) — a future harness lever.

**END-TO-END: the REAL local agent now builds a good scene ITSELF (2026-07-03).** Ran gpt-oss:20b through
the actual runtime on a text task ("build a cozy pond scene using the helpers"), with only the notebook +
render tool. Unprompted on specifics, it wrote a `func build(root)` calling `add_building` (bakery/granary/
nest/well), `add_goose` beside the nest, `add_tree` x4, with the notebook's soft palette and ~3-unit
spacing — a gate-passing village (green 0.50, 3 colours) that looks as good as the hand-authored scenes.
So "teach Icarus the shapes" (one-call helpers + notebook) actually works: the project's core goal — ICARUS
builds the game — now holds for visuals, not just logic. HONEST caveat: the loop ended STUCK (not DONE) —
gpt-oss emitted prose instead of a final tool call after rendering; the scene is still produced + gated
(materialize_templated_scene harvests it regardless). Lead: harden the loop's prose-not-a-tool-call exit.

## CLEAN re-measurement — 15/16 = 0.94, debugging improved (2026-07-03, Step D done right)
Re-ran seed=7 UNAIDED with **zero concurrent load** (the contamination lesson applied): **15/16 = 0.94**,
up from the clean 13/16 = 0.81 baseline. The notable signal: **BOTH debugging tasks PASSED** — `fix_bug`
went fail→PASS (it failed at 13/16) and `fix_range` passed — directly consistent with harness-mod-54 (the
`run` tool now shows Icarus the ACTUAL error at the end of output, not a truncated head, so its "read the
error, fix it" loop works). The only miss was `pondtick` (empty output — a one-off timeout flake).
**HONEST caveat:** n=1, stochastic model — a single run can't *prove* a 2-task debugging effect isn't luck.
But it's directionally encouraging, shows NO regression, and the clean number (0.94) vs the contaminated
one (0.62, same fixes) confirms the "measure clean" methodology. The valid unaided band is now **~0.81–0.94**.

## CONTAMINATED re-run — do NOT read as a regression (2026-07-03)
A seed=7 re-run scored **10/16**, but it is INVALID: I ran pytest (which spawns Godot) + git commits
REPEATEDLY *during* the battery, and the GPU/IO contention degraded it — `place_n8` literally
`PermissionError`-CRASHED (a file conflict), `pondtick`/`granary` returned EMPTY (agent timed out under
load), `fixrange` regressed. Remove those ~3 contention artifacts and it matches the clean **13/16 = 0.81**
baseline; the run-tool fix's effect on debugging is INCONCLUSIVE from a contaminated run (fixbug/fixrange
need a clean measure). **Methodology lesson (binds future measurements): run a capability battery CLEAN —
no concurrent pytest / builds / GPU work — or the number is noise.** The valid unaided figure stays 0.81.

## Harness improvements — observed effect on SCENE building (2026-07-03, Step D)
Five agent-runtime fixes this session (harness-mod-52..56), three of them context-truncation blindfolds
that silently dropped exactly the content Icarus needed: the reviewer saw only 2KB of a scene; Icarus saw
only 2KB of its NOTEBOOK (missing the Godot-4 `.translation` lesson); the `run` tool showed only the first
2KB of output (hiding the error at the end). Plus helper-return (a null-capture crash class) and fast-path
self-verify (render+see templated content mid-loop).

**Observed effect (aided scene path):** OP-35 (pond world + a detailed goose) ESCALATED on its first
attempt pre-fix — Icarus wrote the Godot-3 `.translation` (the very lesson truncated out of its notebook)
and `_ready()` crashed. After the fixes, OP-36 (a HARDER scene: two detailed geese) built **clean on the
first attempt** — full notebook injected, no `.translation` crash, gate + reviewer passed. Anecdotal (n=1
each, stochastic model) but directionally consistent: the fixes give Icarus the lessons + errors it needs.
Structurally proven by targeted tests (the `.translation` lesson now demonstrably reaches the prompt).

## Fresh re-measurement — 2026-07-03 (unaided, gpt-oss:20b, no notebook, seed=7, 16 logic tasks)

**Unaided logic battery: 13/16 = 0.81** — a fresh, honest run of the north star, squarely in the
established 0.73–0.85 band (stable run-to-run; the model is stochastic). PASS (13): sum, reverse, json,
fizzbuzz, fixrange, readsum, find_secret, economy, placement, pond_tick, predator_safety, granary,
pond_score. FAIL (3): `fix_bug` (debugging — the known weak area, normally routed to the 30B, run here on
the fast model unaided), `water_access` (empty output this run — variance), `pond_outcome` (returned
`dry` vs `thriving` on a threshold edge). Confirms Icarus's unaided logic capability is genuinely ~0.8 and
has NOT regressed across the whole session's changes. The real lever to push it higher remains the
external QLoRA fine-tune on the self-distillation corpus (81 pairs, docs/DISTILL.md), not more base-runtime
tweaks (exhausted on the 16GB card).

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

**Broader UNAIDED battery (2026-07-03, 12 domains, fast model, no notebook, single attempt): 10/12 =
0.83.** All game-logic (economy/placement/pond-tick/water) 4/4, coding 5/6 (one JSON miss = variance),
GDScript syntax ✓; the two misses are JSON (variance) and `render` (structurally model-limited unaided
on the fast model — solved operationally by the scene template + routing, not a fundamental leap). This
is the north star with all runtime improvements in place: Icarus unaided is genuinely capable at the
game's logic; the only hard ceiling is complex 3D scene construction on the small resident model.

**Comprehensive unaided-LOGIC battery (2026-07-03, 15 tasks incl. the newly-added predator/granary/score
generators, fast model, no notebook, single attempt): 11/15 = 0.73.** PASS: sum, json, fizzbuzz,
fix_range, read_sum, find_secret, economy, water, **predator, granary, score** (all three new game
mechanics pass). FAIL: reverse, fix_bug, placement, pond_tick — honest caveat: this is **single-attempt
variance** (placement and pond_tick PASSED in earlier runs; reverse is trivially within ability). So the
true unaided-logic rate sits in a ~0.73–0.85 band run-to-run (stochastic model; best-of-N or one
self-repair would lift it). The signal that matters: **the game's own mechanics are solidly in Icarus's
unaided reach** — every One Pond logic generator (economy/water/predator/granary/score) passed this run.

**Corroborated by the data-gen batch (2026-07-03):** `ops/generate_training_data.py` ran 24 FRESH
procedurally-generated logic instances unaided (no notebook) and kept the passing ones — **17/24 = 0.71**,
a different sample landing in the same band. (Those 17 verified solutions are now `data/generated_sft.jsonl`
training data; the 7 failures are just discarded, not hidden.)

## HONEST behaviourally-gated capstone (2026-07-03, post-harness-mod-50): 14/14 @ autonomy 1.0 in 626s
The FIRST full-backlog run where the deterministic `python_behavior` gate actually participated (it was
silently skipped in the earlier 9/9 and 11/11 capstones — see the harness-mod-50 correction below). The
deepened **14-ticket backlog (OP-1..OP-14)** committed **14/14 at autonomy 1.0**, unattended, under BOTH
the behavioural check AND the reviewer now live. OP-13 (the 4-branch advice priority) committed only after
a gate-forced rework — a harder composed rule genuinely tested the now-active gate, and the loop still
landed it within `max_rounds`. So the "behaviourally-gated capstone" claim is finally TRUE, and it holds
at 14/14 @ 1.0. This supersedes the earlier capstones below (which were reviewer-gated only).

## Full-backlog capstone (2026-07-03)
The **entire authored One Pond backlog (OP-1..OP-9)** run through the FULL hardened gate — certified
deterministic checks (`python_syntax`, `godot_parse`, `godot_render`, `python_behavior`) + a real local
Stage-B reviewer (`default_reviewer`, gpt-oss:20b) — committed **9/9 at autonomy 1.0 in 491s** (~8 min),
unattended. A Godot scene (OP-1, templated/fast) + eight logic modules, each gated by its pinned criteria
+ behavioural examples, one passing only after a gate-forced rework. The whole game backlog builds and
commits cleanly under the complete gate — the culminating end-to-end proof.

**RE-VALIDATED on the deepened backlog: 11/11 @ autonomy 1.0 in 561s.** After the game grew from 9 to 11
tickets (water-access + well colour), the full OP-1..OP-11 backlog again committed through the full gate
unattended. OP-11 was the slowest ticket to land; I initially guessed "reviewer friction on correct code"
but **measured it and that was wrong** — the local reviewer PASSES the committed `water_access.py` 5/5
(AC2 PASS, sound evidence). So OP-11's delay was ordinary build+review latency / early build variance the
behavioural gate correctly filtered, NOT a too-strict reviewer. Lesson (logged honestly): measure before
asserting a cause. The deeper game holds up end-to-end at autonomy 1.0.

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
(exact strings + a concrete input→output example, e.g. `tick_bread([...]) == 7`).

**RESOLVED (harness-mod-44/45, then genuinely wired in harness-mod-50): a deterministic behavioural check.**
`PythonBehaviorCheck` runs authored `{module, call, expect}` examples against the produced module and
requires exact results — certified and carried by every logic ticket.
**HONEST CORRECTION (2026-07-03):** it was `register`-ed in `default_registry` at harness-mod-45 but had
`targets=["*.py"]`, which `registry._applies` matches against `ticket.kind` (not filenames) — so it was
SILENTLY SKIPPED in every live Stage-A run until **harness-mod-50** fixed `targets` to `["*"]`. Earlier
claims here that it "live-confirmed" / "mechanically FAILs" a bad build in the pipeline were WRONG: through
the capstones the **reviewer** (Stage B) was the actual enforcer that reworked bad builds; the behavioural
check only ever ran as a unit test. Post-harness-mod-50 it genuinely gates (regression-tested through
`registry.run_stage_a`: a broken module is rejected live). The whack-a-mole is over for exact-output logic
now — but it wasn't between harness-mod-45 and -50. Found via an OP-14 build that committed a module raising
`AttributeError` on its own examples.

## Caveat
An earlier routed full-battery run measured 4/6, but it was the victim of GPU contention (two 30B tasks
overlapping — 31 min; the empty-output failures were starvation artifacts). Trust clean single-model
runs like the one above, not contended ones (see the single-live-run note in `docs/HANDOFF.md`).

## Method
Each generator ships its own deterministic checker; scored UNAIDED (the honest north star). Assisted
(notebook) and routed full-battery runs are also available via `run_battery(..., router=...)`.
