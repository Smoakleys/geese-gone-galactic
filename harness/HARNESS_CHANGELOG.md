# Harness changelog

Every change to `harness/` is logged here with rationale. The self-mod validator
(`harness/selfmod/validator.py`) mechanically rejects a change that touches `harness/`
without a matching entry. Reverts are one command via the token in `harness/reverts.log`.

## harness-mod-0 — Phase 0.5 walking skeleton
- Core data model with `criteria_hash` freeze and default-FAIL verdicts (`models.py`).
- State machine whose only edge into `COMMIT_PENDING` is `STAGE_B_PASS` (`states.py`).
- Check runner with fixture-based certification and `registry.lock` (`checks/`).
- Gatekeeper as sole commit authority + monotonic ratchet (`gatekeeper.py`, `ratchet.py`).
- Stub builder/reviewer + reviewer-isolation packet builder (`icarus/`, `review/`).
- Self-mod validator + revert bookkeeping (`selfmod/`).
- Rationale: prove the governance thesis end-to-end with zero LLM/art cost before wiring
  real reviewers, Icarus, and the art pipeline. See `docs/PLAN.md` Phase 0.5.

## harness-mod-1 — Phase 1 real deterministic check runner
- Explicit `CheckCost` tier (STATIC/STRUCTURAL/DYNAMIC) on the check contract; the registry
  now runs certified checks cheapest-tier-first so a cheap FAIL short-circuits before any
  expensive pixel analysis runs (`checks/base.py`, `checks/registry.py`).
- Real code checks: `python_syntax` (ast.parse), `json_valid` (`checks/code.py`), each with
  committed good/bad fixtures.
- Real CV checks (Pillow, lazily imported to keep the core stdlib-only): `image_loadable`,
  `image_min_resolution`, `image_not_blank` (`checks/image.py`) with image fixtures.
- `CheckResult.metrics` — checks emit higher-is-better numeric signals (min resolution,
  pixel variance); the Gatekeeper mints them as monotonic ratchet floors (`models.py`,
  `gatekeeper.py`).
- `default_registry` certifies all of the above; image checks are skipped only where Pillow
  is absent (an uncertified check is inert, never a rubber stamp).
- Rationale: replace the trivial `non_empty_artifact` placeholder with a real, cost-tiered
  Stage A that catches broken/blank/tiny art and code deterministically, and make quality
  floors ratchet on real measurements. See `docs/EXECUTION_PLAN.md` Phase 1.

## harness-mod-2 — Phase 2 reviewers + four anti-complacency teeth
- Model-client seam (`review/model_client.py`): `ChatClient` protocol, deterministic
  `ScriptedChatClient` for offline tests, optional lazily-imported `AnthropicChatClient` for
  a real fresh-session Opus reviewer. Models answer per-criterion only; the overall verdict
  stays derived/default-FAIL.
- `LLMReviewer` (`review/llm_reviewer.py`): real Stage-B reviewer behind the seam; decomposes
  the isolated packet into one question per criterion, fresh reviewer id per round,
  evidence-required.
- Multi-model `ConsensusReviewer` (`review/consensus.py`): unanimity required, fails closed on
  any disagreement — catches a single-model wrong verdict; can only tighten, never loosen.
- Visual gate (`review/visual_gate.py`): decomposed CV signals (variance, resolution, edge
  coherence, palette) + reference-anchored histogram similarity; validated by
  `evaluate_labeled_set` against a committed labeled good/bad image set (verification item 7).
- Plateau detection (`metrics/plateau.py`) wired into `loop.py` as an independent escalation
  trigger (stuck defect signature OR no score gain over a window), distinct from the
  max-rounds ceiling.
- Cold audits (`audit/cold_audit.py`): re-verify accepted artifacts mechanically (checks +
  hashes) and optionally via a fresh cold re-review; any finding hard-blocks.
- Decision-log -> new-check flywheel (`review/decision_log_review.py`): Stage C reads decision
  logs / recurring subjective defects and proposes deterministic checks (taste→gate).
- Rationale: turn the stubbed reviewer into real, adversarial, multi-lens Stage B and stand up
  the anti-coasting teeth. Real LLM/vision calls sit behind seams so the suite stays offline.
  See `docs/EXECUTION_PLAN.md` Phase 2.

## harness-mod-3 — Phase 3 Icarus builder seam
- `LLMBuilder` (`icarus/llm_builder.py`): real Icarus behind a swappable `GenerationClient`
  seam (scripted offline; local-model/API drop-in). Writes only to staging, has no commit
  path, honestly returns `GAVE_UP` on empty output, and records handed-down defects to the
  decision log to feed the Stage-C flywheel.
- Rationale: replace `StubBuilder` with the real builder shape without touching the loop or
  gate. The control surface that drives it lives in the (non-harness) `control/` package. See
  `docs/EXECUTION_PLAN.md` Phase 3.

## harness-mod-4 — Phase 3.5 text-to-3D worker seam
- `harness/gen3d/`: `MeshGenerator` contract returning an `Asset` (mesh + previewable image);
  `CuratedPackWorker` (guaranteed offline fallback from a committed low-poly pack),
  `ProceduralStubWorker` (simulates a GPU model of a given quality), and a lazily-imported
  `RemoteGpuWorker` real seam.
- `select_generator`: measures each candidate's preview with the same reference-anchored visual
  gate as Stage B and picks the first that passes, falling back to the curated pack (and
  reporting it) when none do — the GPU dependency can never stall or degrade the pipeline.
- Committed curated pack (`gen3d/curated/{bakery,hut}`) whose previews pass the gate.
- Rationale: de-risk the biggest external unknown (local text-to-3D needs a GPU we don't have)
  by making the generator swappable and quality-selected, with a shippable fallback. See
  `docs/EXECUTION_PLAN.md` Phase 3.5.

## harness-mod-5 — wire the ratchet floor gate into the Gatekeeper
- `RatchetStore.check_floors` was dead code: the monotonic ratchet kept a floor from *dropping
  in storage* (`raise_floors` = max), but nothing refused a candidate artifact whose measured
  quality had regressed *below* an established floor — so a worse re-build of a ticket could be
  committed while the stored floor silently stayed high. That is the exact "quality silently
  regressed" failure the ratchet exists to make impossible (`docs/PLAN.md` teeth #2).
- `Gatekeeper.try_commit` now computes the candidate's baseline metrics *before* promotion and
  calls `check_floors`; any metric below its floor short-circuits with `CommitOutcome(committed=
  False, reason="ratchet floor regression: …")` — no promotion, no `git commit`, no floor/fixture
  mint, and the existing accepted artifact is left untouched (`gatekeeper.py`).
- `_baseline_metrics` refactored to measure from a source dir + explicit ticket id, counting only
  the files that will actually be promoted (non-empty, non-forbidden), so the metrics checked
  pre-promotion match the committed artifact exactly; the mint path reuses that same dict.
- First commit of any ticket is unaffected (no prior floor for its keys → no violation); metrics
  are ticket-scoped so tickets never cross-block each other.
- Rationale: make the monotonic ratchet a real *gate*, not just a storage invariant — closing
  verification item "Ratchet holds" (`docs/PLAN.md`). See tests in `test_walking_skeleton.py`.

## harness-mod-6 — Stage C distinguishes "no gate" from "gate too lax"
- `DecisionLogReview.analyze` gained an optional `existing_check_ids` argument. A recurring
  subjective defect whose `criterion` is *already a certified check* now yields a
  `tighten_rubric` proposal (the mechanical gate exists yet reviewers still reject it, so it is
  too lax) instead of a redundant `new_check`; novel criteria still yield `new_check`. Without
  the argument, behaviour is unchanged (all `new_check`), so existing callers are unaffected.
- `AutonomousRunner.harvest_stage_c` passes `registry.certified_checks()` ids in, so the live
  pipeline makes the distinction automatically.
- Rationale: the flywheel's job is to spend expensive judgement only on genuinely new questions;
  proposing a brand-new check for a defect a check already covers is noise. Telling "write the
  missing gate" apart from "tighten the existing gate" makes the taste→gate suggestions
  actionable. No checks/floors/fixtures touched. See `tests/test_phase2_reviewers.py`.

## harness-mod-7 — deterministic code checks are total functions (never crash the loop)
- `PythonSyntaxCheck` and `JsonValidCheck` only caught `SyntaxError` / `JSONDecodeError`. A
  candidate file that was undecodable text (non-UTF-8 bytes -> `UnicodeDecodeError` from
  `read_text`) or contained null bytes (`ast.parse` raises `ValueError`, not `SyntaxError`) would
  raise *out of the check*, propagate through `run_stage_a`, and crash the whole ticket instead of
  being recorded as a clean Stage-A FAIL. That is the CV checks' existing posture (`image.py`
  catches broadly and FAILs); the code checks were the inconsistent outlier.
- Both checks now read the file and parse under guarded `except`s: an unreadable/undecodable file
  or null-byte source is a `Result.FAIL` with evidence, never an exception. Valid files are
  unchanged (still PASS), broken-but-decodable files still FAIL with the same messages, so
  certification against the committed good/bad fixtures is unaffected.
- Rationale: a check must be a *total* function of `(artifact_dir, ticket)` — a builder shipping a
  pathological file is a defect to gate, not a way to crash the harness. Keeps the loop robust
  against adversarial/garbled builder output. See `tests/test_phase1_checks.py`.

## harness-mod-8 — Stage A is fail-closed against a check that raises
- `Registry.run_stage_a` wrapped each `check.run(...)` in a guard: an unexpected exception from
  any check now becomes a `Result.FAIL` (`"check raised <Type>: ..."`) instead of propagating out
  of Stage A and crashing the whole ticket. Certification only proves a check against its fixtures,
  so a check can pass certification yet raise on an unusual/adversarial artifact (exactly the
  `game/onepond/checks.py` malformed-config crash that was just fixed per-check) — this makes the
  "a check never crashes the loop" guarantee *structural* at the runner, not a property each check
  must individually remember to uphold.
- Fail-closed on purpose: an erroring check is treated as a rejection, never a pass, so a crash can
  never wave bad work through. Normal PASS/FAIL/SKIP behaviour is unchanged.
- Rationale: same anti-complacency thesis as the rest of the harness — structural guarantees over
  discipline. See `tests/test_phase1_checks.py`.

## harness-mod-9 — Stage B is fail-closed against a reviewer that raises
- The loop called `self.reviewer.review(...)` unguarded: any exception from the reviewer — a
  production model/network failure, a scripted-client bug — propagated out and crashed the whole
  ticket. Symmetric to harness-mod-8 (Stage A), the loop now catches it and synthesizes a
  blocking `review` defect verdict (`reviewer_id="loop-guard"`), so the round takes the normal
  rework/escalate path instead of dying.
- Fail-closed: a reviewer error is a rejection, never a pass — no work is committed on the back of
  a failed review. A transient failure therefore costs a rework round (and, on plateau, an
  escape-hatch escalation), never the run.
- Rationale: the standing order is "run unattended"; a network blip mid-review must not be able to
  take the build down. Structural resilience over hope. See `tests/test_phase3_control.py`.

## harness-mod-10 — the builder call is fail-closed too (completing the trio)
- The loop called `self.builder.build(packet)` unguarded, so an exception from the builder — a
  generation-client model/network failure, an I/O error — propagated out and crashed the ticket.
  Completing the set with harness-mod-8 (checks) and harness-mod-9 (reviewers), the loop now
  catches it, discards any partial staging output (`_reset_dir`), and lets Stage A judge the
  resulting empty build: `non_empty_artifact` FAILs, so the round reworks/escalates like any other
  rejection. No single actor in the loop — builder, check, or reviewer — can crash the unattended
  run.
- Fail-closed: a build error yields no acceptable artifact, never a commit. Partial/garbled output
  is thrown away rather than judged, so a mid-write crash can't accidentally pass Stage A.
- Rationale: "run unattended" means the three moving parts of every round must each degrade to a
  rejection, not a crash. See `tests/test_phase3_control.py`.

## harness-mod-11 — idempotent re-accept (a re-run of an unchanged ticket isn't a failure)
- `Gatekeeper._git_commit` unconditionally ran `git commit`; re-accepting a ticket whose promoted
  bytes are identical to what's already committed produced "nothing to commit" (a non-zero git
  exit), which propagated out and the runner recorded the ticket as blocked/errored. Re-running an
  unattended build over a persistent workspace therefore "blocked" every already-done ticket.
- Now the commit is skipped when `git diff --cached --quiet` shows nothing staged; the existing
  HEAD sha is returned. Re-accepting an unchanged, still-valid artifact is idempotent SUCCESS
  (committed=True, same sha) — a first-time accept, or any real byte change, still commits exactly
  as before. Preserves the one invariant (commit authority stays here) and the ratchet.
- Rationale: "run unattended" implies safe, repeatable re-runs; a no-op re-accept must not look
  like a regression. See `tests/test_walking_skeleton.py`.

## harness-mod-12 — Icarus' agent runtime (plan->act->reflect walking skeleton)
- New `harness/icarus/agent/`: replaces one-shot generation with a plan->act->reflect agent loop —
  the thing that turns the local model into something that can investigate, act, observe, and adapt.
  `runtime.py`: a forgiving text tool-protocol parser (`parse_tool_call`, one ```tool block/turn —
  local models are weak at strict JSON function-calling); sandboxed `exec_tool`
  (write_file/read_file/run/finish, path-escape-guarded, output-capped, never raises); an
  `AgentModel` chat seam with a deterministic `ScriptedAgentModel` for offline tests; and
  `run_agent` (the loop — states DONE/MAX_STEPS/STUCK; captures the stated PLAN as the approach
  artifact and the full transcript as the trajectory the critic + scorecard inspect).
  `ollama.py`: `OllamaAgentModel` (local chat brain, `POST /api/chat`, gpt-oss:20b default).
- Gate untouched: no checks, floors, fixtures, gatekeeper, reviewer, or ratchet changed. This is
  "Icarus' harness" (the builder side), kept strictly separate from the gate; the runtime writes
  only into a sandboxed workspace and has no commit path.
- Rationale: the north star is Icarus's *unaided* problem-solving, and a one-shot generator cannot
  investigate/observe/adapt. This is the walking skeleton of the agent loop I improve every cycle;
  perception (see-screenshot via the vision model), codebase/doc search, and the durable notebook
  are the next measured upgrades. Tested offline (scripted model): loop end-to-end + protocol +
  sandbox escape + failure reflection. See `tests/test_agent_runtime.py`.
- Live-verified: the loop drove **gpt-oss:20b** to write `greet.py`, RUN it to verify its output,
  and finish (5 steps, ~20s). Prompt tuned for reasoning models — an over-instructed system prompt
  makes gpt-oss leave `content` empty (all in the `thinking` channel), so the prompt is a short
  "exactly one tool block, nothing else" form and `OllamaAgentModel` falls back to `thinking` when
  `content` is empty. Occasional reasoning-only turns are recovered by the loop's reflect step;
  higher-reliability tool emission (native tool-calls) is a future measured improvement.

## harness-mod-13 - Icarus gains eyes + code exploration (see / list_files / search)
- harness/icarus/agent/: three new tools on the runtime. `list_files` and `search` (regex with a
  literal fallback) let Icarus explore a codebase instead of writing blind. `see` - a new `VisionModel`
  seam (`vision.py` = `OllamaVisionModel` on qwen2.5vl:7b) - lets Icarus LOOK at an image and reason
  about it. `exec_tool`/`run_agent` gained an optional `vision` param; `see` is disabled fail-safe when
  no vision model is wired. All sandbox-scoped, output-capped, never-raise.
- Live-verified: qwen2.5vl:7b described the Godot iso render ("a green square, diagonal orientation,
  on a gray background") - Icarus can now see what it builds, the prerequisite for the visual-gate loop.
- Gate untouched. Tested offline (scripted vision stub + fs/search tools). See tests/test_agent_runtime.py.

## harness-mod-14 - Icarus gains a durable notebook (cross-task memory)
- harness/icarus/agent/notebook.py: a plain-markdown Notebook (read/append/entries, cheap de-dup).
  New `note` tool lets Icarus save a lesson/strategy; run_agent injects the notebook at task start so
  the agent stops re-learning the same things. exec_tool/run_agent gained a `notebook` param and a
  `use_notebook` flag - use_notebook=False strips the memory to measure UNAIDED capability (the
  dependence-gap discipline: every crutch we add, we can remove to check the skill actually stuck).
- Gate untouched. Tested offline: notebook append/de-dup, the note tool, injection + strip-to-test.

## harness-mod-15 - Icarus capability battery + scorer (the honest scorecard begins)
- harness/icarus/eval/: procedural task GENERATORS (arithmetic/strings/config/logic), each emitting a
  fresh randomized TaskInstance with its OWN deterministic verifier that RUNS the produced code
  (Reasoning-Gym lesson: infinite, non-memorizable instances; a pass means it works, not that it looked
  right). run_battery drives the agent loop and reports pass rate; default use_notebook=False = the
  north-star UNAIDED score (gap to the assisted score = the dependence-gap metric).
- First live reading: gpt-oss:20b scored 4/4 unaided on the seed-0 battery (sum, reverse, JSON,
  FizzBuzz) - a real, honest baseline. The tasks are basic; the point is the scorecard now exists and
  will climb (and get harder) measurably.
- Gate untouched. Tested offline: reproducible/varying sampling, verifier pass/fail, runner scoring.

## harness-mod-16 - Resilience + harder capability tasks (no single blip takes Icarus down)
- harness/icarus/agent/: OllamaAgentModel now RETRIES transient failures (Ollama's HTTP 500 during a
  model reload) with backoff; run_agent guards model.complete so a persistent model/network failure
  degrades to STUCK instead of crashing the loop. (A transient 500 previously crashed a whole battery.)
- harness/icarus/eval/capability.py: TaskInstance gained an optional `setup` hook (seed the workspace);
  three harder generators - fixbug (debug a broken file), read_sum (multi-file read-then-compute),
  find_secret (search) - make the scorecard discriminating. run_battery guards run_agent so one task
  crashing never kills the run.
- Gate untouched. Tested: retry-degrades-to-stuck, setup/verifiers, battery resilience.

## harness-mod-17 - GDScript on the scorecard (the game domain enters the battery)
- harness/icarus/eval/capability.py: gen_gdscript - Icarus writes a Godot 4 GDScript scene (Node3D
  with a Camera3D + N BoxMesh children), verified by `godot --check-only` (the exact check command is
  handed to Icarus so it can self-verify with the run tool). Added to default_generators, so the honest
  battery now measures the REAL domain, not just Python.
- Live: gpt-oss:20b scored 8/8 unaided incl. GDScript (3/3 GDScript-only) - it writes valid GDScript 4
  and self-checks. The syntax bar is easy; semantic RENDER tasks (must draw the right thing) are next.
- Gate untouched.

## harness-mod-18 - Icarus can render (visual feedback tool) + the render bar discriminates
- game/godot/capture.py: render_gdscript renders a loose scene.gd off-screen via the rig (capture.gd
  gained --script: attach a GDScript to a Node3D and render) to a PNG; image_variance = blank/not-blank.
- harness/icarus/agent/: new `render` tool (injected render_fn seam, like vision) so Icarus can turn a
  scene file into a PNG and then `see` it. run_agent/run_battery thread render_fn.
- harness/icarus/eval/capability.py: gen_render - a SEMANTIC task (the scene must actually RENDER
  non-blank, not just parse). The FIRST discriminating task: gpt-oss:20b scored 1/3 unaided (2 scenes
  rendered blank - camera not current / wrong material).
- HONEST negative result: wiring render+see into the task prompt REGRESSED the score to 0/3 (the verbose
  prompt re-triggered gpt-oss's reasoning-only failure; the weak 7B vision likely rubber-stamped blank
  renders). Per the gym rule (keep only measured improvements), the prompt was reverted; the render tool
  stays for a future, more capable setup (the bake-off / a stronger vision judge).
- Gate untouched. 195 tests. Render tool tested offline; render pipeline verified live.

## harness-mod-19 - Render feedback made deterministic; the render limit is model knowledge, not scaffolding
- game/godot/capture.py: render_gdscript now surfaces the pixel VARIANCE in its result (e.g.
  "variance 0.0 - BLANK"), so the render tool gives Icarus a reliable blank-detector instead of relying
  on the weak 7B vision model. gen_render prompt tightened to point at it.
- Measured honestly: this did NOT lift the render score (still 1/3 unaided; the earlier see-based loop
  had regressed it to 0/3). gpt-oss:20b renders 2/3 scenes blank even WITH a deterministic blank signal -
  it cannot reliably fix a non-rendering 3D scene. The bottleneck is the model's 3D-scene knowledge, not
  the feedback. Per the gym rule, scaffolding that doesn't move the score isn't the lever here: the real
  lever is model capability (the brain bake-off) or learned 3D patterns. Gate untouched. 195 tests.

## harness-mod-20 - CRITICAL: the render verifier was broken (variance != blank); Icarus renders 3/3
- game/godot/capture.py: the render blank-check was `variance >= 6`, which wrongly FAILS a valid render
  that fills the frame with a solid colour (uniform pixels have ~0 variance). Replaced with brightness
  (brightest_mean < BLANK_FLOOR == near-black == blank). A bright-green ground plane filling the view is
  now correctly a PASS. gen_render verify updated to match; regression test added.
- Impact / correction: this bug caused FALSE render failures and misled harness-mod-18/19. Re-checking
  the actual renders Icarus produced, its true UNAIDED render score is 3/3 = 1.00, NOT 1/3. gpt-oss:20b
  renders correctly; the seeded notebook lessons (look_at AFTER add_child; `size` not `orthogonal_size`)
  even helped it. The "model can't do 3D / scaffolding doesn't help" conclusions were artifacts of a bad
  gate, now retracted.
- Lesson (the harness's core thesis): a bad verifier corrupts the whole improvement loop; LOOKING at the
  actual artifact (Reading the PNG) is what caught it - I nearly pulled 50GB of models chasing a phantom
  limit. 196 tests.

## harness-mod-21 - AgentBuilder: Icarus's agent runtime behind the Builder seam
- harness/icarus/agent_builder.py: AgentBuilder wraps the plan->act->reflect loop as a Builder, so the
  gatekeeper-fronted loop can build real tickets with the AGENT (tools/perception/memory) instead of a
  one-shot generator. task_from_packet turns a ticket (+ rework defects) into the agent's task; writes
  only into staging (no commit path); COMPLETED iff it produced files, else GAVE_UP (triggers the escape
  hatch). Connects the two harnesses (agent runtime <-> gate) - the prerequisite for the first committed
  Godot artifact built by Icarus.
- Gate untouched. Tested offline (scripted): completes+logs, gave-up-when-no-files, task construction.

## harness-mod-22 - CORRECTION: render gate is green-DOMINANCE (harness-mod-20's brightness fix was wrong)
- The render gate has now been through THREE forms, each corrected by LOOKING at real renders:
  variance (false-FAILS a valid uniform green fill) -> brightness (false-PASSES a uniform GRAY
  background, i.e. an EMPTY render where the camera saw nothing -> harness-mod-20's "3/3" was inflated)
  -> green_dominance = g - max(r,b) (passes a real green scene; fails gray/empty AND black). Correct now.
- game/godot/capture.py: added channel_means + green_dominance; render_gdscript reports mean RGB and
  flags "looks EMPTY (uniform background)". gen_render verify uses green_dominance>=15. Regression test
  covers green(pass) / gray(fail) / black(fail).
- Honest correction: harness-mod-20's claim "Icarus renders 3/3, the gate was broken" was itself WRONG -
  the failing renders were genuinely gray/empty (the look_at-before-add_child bug leaves the camera aimed
  at the background). Unaided render capability is low; the seeded notebook (look_at lesson) is what makes
  it render green - a real, measured improvement. 202 tests.

## harness-mod-23 - Bread-economy task on the scorecard (Icarus's game-logic strength: 3/3)
- harness/icarus/eval/capability.py: gen_economy - a procedural goose-pond bread-economy simulation
  (the real game's LOGIC domain), added to the battery. Icarus scored 3/3 unaided on gpt-oss:20b
  (correct economy math over N ticks). Confirms the strategic read: Icarus is strong at game
  SYSTEMS/logic - exactly where the mission needs it - even as it is weak at 3D visual rendering.
  Regression test covers the verifier. 206 tests.

## harness-mod-24 - Model routing: bigger model for visual tickets (validated by data)
- Decisive Task-4 finding: qwen3:30b renders Godot 3D scenes 3/3, where gpt-oss:20b and qwen2.5-coder:14b
  fail 0/3. The visual limit is model SIZE, not a hard local ceiling.
- harness/icarus/agent_builder.py: ModelRouter (model-as-free-variable - keyword rules pick the model
  per task) + visual_router(fast, big) (visual/render/Godot keywords -> big, else fast). AgentBuilder
  now accepts a router and selects the model per ticket, so Icarus uses fast gpt-oss:20b for logic
  tickets and the 30B for visual ones - best of both. Tested offline (routing + per-ticket selection). 209 tests.

## harness-mod-25 - Placement mechanic on the scorecard (breadth phase begins)
- harness/icarus/eval/capability.py: gen_placement - a procedural building-placement validation task
  (in-bounds + no-overlap on the pond grid), a real One Pond mechanic in Icarus's strength (logic).
  Regression test covers the verifier. Begins the breadth phase: growing the scorecard + the game with
  its actual systems, one ticket at a time. 212 tests.

## harness-mod-26 - Routing-aware scorecard (measure the ASSEMBLED Icarus)
- harness/icarus/eval/capability.py: run_battery accepts a `router` (ModelRouter), so each task runs on
  its best model (visual/render -> 30B, logic -> fast gpt-oss:20b) - the honest score of the assembled
  Icarus, not a single model handicapped on the wrong domain. Tests cover routed scoring + the
  model-or-router guard. 214 tests.

## harness-mod-27 - Faster hung-call failure + single-live-run discipline
- harness/icarus/agent/ollama.py: default model-call timeout 600s -> 240s, so a hung Ollama call (e.g.
  GPU contention) fails fast and the loop degrades to STUCK instead of blocking ~10 minutes.
- docs/HANDOFF.md: recorded the "one live model run at a time on the 16GB GPU" discipline - concurrent
  live-model tasks (esp. both needing the 30B) thrash/hang (learned the hard way: two overlapping live
  probes stalled). 214 tests.

## harness-mod-28 - Bakery scene task: a building on the ground (breadth)
- harness/icarus/eval/capability.py: gen_bakery_scene - a visual task (routes to the 30B) requiring a
  scene with a green ground AND a distinctly-coloured building box on it. Gated by green_dominance
  (ground visible) + significant_colors>=3 (a building region present, not a bare plane). Verify tested
  offline via synthetic renders (monkeypatched); live confirmation runs when the GPU is free (one live
  run at a time). 216 tests.

## harness-mod-29 - The flywheel works with the real agent (AgentBuilder logs rework defects)
- AgentBuilder._write_decision_log now records the defects Icarus was handed for rework as
  {"defect": {...}} lines (the format Stage C's load_defect_records harvests). Previously the agent's
  decision log had only plan/outcome, so recurring subjective failures from Icarus's runs never reached
  Stage C - the taste->gate flywheel (a core anti-complacency tooth) was inert for the real agent. Now
  it harvests. Test proves a handed-down defect is harvestable. 217 tests.

## harness-mod-30 - Pond scene task + region-based colour detection (breadth)
- game/godot/capture.py: color_fraction(png, kind) - per-pixel channel-dominance fraction, so a scene
  with green land AND a blue pond (whose channel MEANS wash out to muddy grey) is still gradeable.
- harness/icarus/eval/capability.py: gen_pond_scene - the namesake One Pond scene (green land + blue
  water pond + a building), gated by green-land fraction + blue-water fraction + significant_colors>=3.
  Offline-tested (monkeypatched renders); live build routes to the 30B. 220 tests.

## harness-mod-31 - Pond-tick task: the bread tick wired to placement (breadth)
- harness/icarus/eval/capability.py: gen_pond_tick - a One Pond mechanic combining placement validation
  (in-bounds + no-overlap) with the bread economy (bakeries +3/tick, nests -1/tick): validate the layout,
  print INVALID if bad, else the final bread. Icarus's logic strength; on the default battery. Regression
  test covers the verifier. 225 tests.

## harness-mod-32 - Forgiving parse of an unclosed tool block (Icarus runtime robustness)
- harness/icarus/agent/runtime.py: parse_tool_call now falls back to parsing an UNCLOSED ```tool block
  (the model dropped the closing fence, or its output was truncated at the context limit) instead of
  returning None and wasting the turn. STRICT improvement: a properly closed block always wins, and the
  fallback only fires when parse would otherwise be None -- so it can never lower a score, only recover
  turns that were previously lost. Tests cover the unclosed recovery + closed-block-preference. 228 tests.

## harness-mod-33 - Water-access task: a spatial One Pond rule (breadth)
- harness/icarus/eval/capability.py: gen_water_access - every goose nest must be within a Manhattan
  reach of the pond's water (SAFE/UNSAFE), a distinct SPATIAL mechanic (vs the count-based economy /
  placement tasks). Icarus's logic strength; on the default battery. Regression test covers it. 229 tests.

## harness-mod-34 - Second debugging task (off-by-one) to characterize the weakness
- harness/icarus/eval/capability.py: gen_fix_range_bug - a DIFFERENT debugging task (fix an off-by-one
  range bug summing 1..n, vs fix_bug's wrong-operator bug), so the scorecard's debugging weakness can be
  read as general vs one-bug-type. On the default battery. Regression test covers the verifier. 230 tests.

## harness-mod-35 - Route debugging to the 30B (measured win: 4/4 vs 2/4)
- Confirmed the scorecard's debugging lever: qwen3:30b scores 4/4 on the same fix-it seeds where
  gpt-oss:20b scores 2/4 -- model SIZE is the lever, same as visuals.
- harness/icarus/agent_builder.py: visual_router now also routes debug/fix-it keywords (_DEBUG_KEYWORDS)
  to the big model, so AgentBuilder / default_icarus_builder send debugging tickets to the 30B. Kept per
  the plan (unaided debugging 2/4 -> 4/4 when routed). Test covers debug routing. 231 tests.

## harness-mod-36 - Speed: context trimming + keep_alive (bound per-turn cost on long runs)
- The agent loop never trimmed history, so a long/reworking run reprocessed an ever-growing context each
  turn -- the main cost of the ~20-min offloaded-30B scene builds (prompt reprocessing on the offloaded
  model). harness/icarus/agent/runtime.py: _trim_context keeps the setup (system + task/notebook) + the
  most-recent 8 exchanges, collapsing older middle turns to a one-line marker carrying the plan; the full
  transcript is untouched, only the model INPUT is bounded (the plan's "trim raw tool output after use").
- harness/icarus/agent/ollama.py: keep_alive="30m" (model stays resident -> no per-turn reload of the
  offloaded 30B) + optional num_predict cap. Tests cover trimming behaviour. 238 tests.

## harness-mod-37 - Scene template + gen_pond_from_template (speed path for visuals)
- harness/icarus/eval/capability.py: gen_pond_from_template - Icarus writes only build(root); the verify
  composes it with a camera template (game/godot/scene_template.py) + renders + gates. Lets the FAST
  resident model attempt real scenes. Measured: fast model 1/3 (camera now correct, but content errors
  like rotating a PlaneMesh vertical) - a partial win; the 30B stays the reliable scene builder. Notebook
  gained the plane-rotation gotcha. 239 tests. See docs/SPEED.md.

## harness-mod-38 - Content helpers solve visual speed (fast model 4/4 @ ~19s vs 30B ~200s)
- game/godot/scene_template.py: added add_plane / add_box helpers to the template; Icarus supplies only
  params (size/colour/position) and cannot botch mesh/rotation/material.
- harness/icarus/eval/capability.py: gen_pond_from_template prompt now directs Icarus to call the helpers.
- MEASURED: the FAST resident gpt-oss:20b builds real pond scenes 4/4 at ~19s/scene -- ~10x faster than
  the offloaded 30B (3/3 ~200s) AND reliable. The visual speed problem is solved by scaffolding, not a
  bigger model. See docs/SPEED.md. 239 tests.

## harness-mod-39 - Route templated scene tasks to the fast model
- harness/icarus/agent_builder.py: visual_router now routes TEMPLATED scene tasks (mention add_plane/
  add_box/content.gd/func build) to the FAST resident model -- checked before the visual rule, so a
  helper-based scene doesn't wrongly hit the offloaded 30B just because it says "camera". Open-ended
  visuals + debugging still route to the 30B. Locks in the speed win (fast templated scenes 4/4 @ ~19s).
  Test covers templated->fast vs open-ended->big. 240 tests.

## harness-mod-40 - Post-build hook: templated scenes flow into the live commit pipeline
- harness/icarus/agent_builder.py: AgentBuilder gains a generic post_build(artifact_dir) hook (runs after
  the agent, before gating; failures non-fatal) -- keeps the harness game-agnostic.
- game/godot/scene_template.py: materialize_templated_scene composes a templated content.gd -> full
  scene.gd (no-op if scene.gd exists / no build content). default_icarus_builder wires it as post_build.
  So a templated scene ticket: Icarus writes content.gd (fast model) -> composed to scene.gd -> gated by
  godot_parse/godot_render -> committed. Tests cover the hook + compose. 242 tests.

## harness-mod-41 - Robust scene compose (extract build(); ignore stray extends/redefined helpers)
- game/godot/scene_template.py: compose_scene now extracts ONLY the agent's func build(root) and always
  provides the correct camera + add_plane/add_box, discarding a stray `extends` header or buggy helper
  redefinitions the local model sometimes adds (duplicate extends / duplicate func / Godot-3 API in the
  redefs all blanked the render). Verified on two real live failures (both now render green ~78).
- harness/icarus/eval/capability.py: gen_pond_from_template verify skips its own _composed_scene.gd when
  finding the agent's content (was picking up stale output across calls). 243 tests.

## harness-mod-43 - Local Ollama Stage-B reviewer client (close the StubReviewer gap)
- harness/review/model_client.py: OllamaChatClient -- a LOCAL, no-cloud-key Stage-B reviewer behind the
  same ChatClient seam, reusing the tested _render_prompt/_parse_answers (so the default-FAIL contract
  holds: a criterion not clearly PASSed is a FAIL). Fails CLOSED on any transport/parse error (all FAIL) --
  a reviewer that can't answer never waves work through. Lets LLMReviewer run a real subjective review
  unattended (the gap OP-6's \n bug exposed). Point it at a model different from the builder for an
  independent critic. Test covers the fail-closed contract. 257 tests.

## harness-mod-44 - Deterministic behavioural check for logic tickets (end the criterion whack-a-mole)
- harness/models.py: Ticket gains an optional `behavior` field (list of {module, call, expect}); NOT part
  of criteria_hash.
- harness/checks/behavior.py: PythonBehaviorCheck runs each example against the produced module and
  requires the EXACT result -- makes exact-output correctness mechanical, catching typos (OP-6 \n, OP-8
  'baker') a subjective reviewer misses. Reads examples from artifact_dir/_behavior.json (certifies vs
  fixtures) else ticket.behavior. SKIP with no examples; fail-closed on missing module / crash / mismatch.
  Certified good/bad fixtures. 274 tests.

## harness-mod-45 - Wire PythonBehaviorCheck into the default pipeline
- harness/checks/builtin.py: default_registry now registers PythonBehaviorCheck. Any ticket carrying
  `behavior` examples (e.g. OP-8) now gets a DETERMINISTIC exact-output gate in the live pipeline -- the
  'baker'/'bakery'-class typo is caught mechanically at Stage A, not left to subjective review.
  Behaviour-less tickets SKIP it (no effect on existing tickets/tests). 274 tests.

## harness-mod-46 - Grow the capability battery: gen_predator_safety
- harness/icarus/eval/capability.py: added `gen_predator_safety` (parameterized nests + fences + reach ->
  SAFE/UNSAFE, deterministic checker) and registered it in `default_generators()`. Grows the sealed
  unaided battery to cover predator safety (a core One Pond mechanic that previously had no generator),
  per the plan's "grow the battery with each mechanic". Verifier tested pass+fail. 297 tests.

## harness-mod-47 - Grow the capability battery: gen_granary
- harness/icarus/eval/capability.py: added `gen_granary` (bakeries*(3+granaries) synergy formula,
  deterministic checker) + registered in `default_generators()`. Covers the granary-synergy mechanic in
  the sealed unaided battery. Verifier tested pass+fail. 298 tests.

## harness-mod-48 - Grow the capability battery: gen_pond_score
- harness/icarus/eval/capability.py: added `gen_pond_score` (bread + weighted building values, deterministic
  checker) + registered in `default_generators()`. The sealed unaided battery now covers the game-logic
  breadth: economy, placement, pond-tick, water, predator, granary, score. Verifier tested. 299 tests.

## harness-mod-49 - Grow the capability battery: gen_pond_outcome
- harness/icarus/eval/capability.py: added `gen_pond_outcome` (the layered bread->water->safety->thriving
  evaluation, a composed multi-branch rule harder than the arithmetic tasks; deterministic checker) +
  registered it. The sealed battery now covers the full One Pond logic surface. Verifier tested. 307 tests.

## harness-mod-50 - FIX: python_behavior was silently SKIPPED in the live pipeline
- harness/checks/behavior.py: `targets` was `["*.py"]`, but registry._applies matches `targets` against
  `ticket.kind` (e.g. "system"), NOT filenames -> the behavioural check never applied to any real ticket
  and was SKIPPED in every live Stage-A run. A behaviourally-broken module could pass the gate (found via
  an OP-14 build that committed a module raising AttributeError on its own examples). Fixed to `["*"]`.
  Added a regression test that runs the check THROUGH registry.run_stage_a (prior tests only called
  check.run() directly and missed the _applies filter). The reviewer had been the actual enforcer; now the
  deterministic behavioural gate is too, as originally intended. 309 tests.

## harness-mod-51 - Self-distillation SFT data pipeline (PLAN Levers 3 & 5)
- harness/icarus/distill.py: `build_sft_records(tickets, module_dir)` + `write_jsonl` turn gate-passing
  (ticket -> committed module) pairs into standard `{instruction, input, output}` QLoRA training records --
  Icarus's OWN verified successes as free fine-tuning data (the plan's real lever for raising *unaided*
  capability beyond the base-model ceiling). Only distills modules that cleared the gate. Generated
  data/onepond_sft.jsonl (the One Pond solutions). The QLoRA run itself is an external GPU step. 328 tests.

## harness-mod-52 - Reviewer sees the full artifact (raise per-file cap 2000 -> 6000)
- harness/review/model_client.py: `_render_prompt` capped each artifact at 2000 chars. A templated Godot
  scene is camera + helpers (~1815 chars) + `build()`, so the cap cut off the actual scene logic and the
  Stage-B reviewer judged scenes nearly blind (found while debugging why OP-33's goose kept escalating).
  Raised to a named `_ARTIFACT_CHAR_CAP = 6000` so a full scene / long module is visible, still well inside
  num_ctx 8192. HONEST SCOPE: this removes the truncation blindfold only; for abstract low-poly scenes even
  a fully-fed TEXT reviewer is an unreliable visual judge (see memory ggg-abstract-visuals-fail-judges) --
  the real lever for goose-recognizability is art or a vision gate, not this. 367 tests.

## harness-mod-53 - Inject the WHOLE curated notebook (cap 2000 -> 8000)
- harness/icarus/agent/runtime.py: run_agent injected only `nb[:2000]` of the notebook. The curated Godot
  seed is 3117 chars, so the LATER lessons (5 of them, incl. the Godot-4 "`.position` not `.translation`"
  rule at char ~2586) were silently cut off -- Icarus never saw them and then made exactly that
  `.translation` mistake in OP-35. Raised to a named `_NOTEBOOK_CHAR_CAP = 8000` so the whole curated,
  high-signal seed is injected within num_ctx 8192. Same truncation-blindfold class as harness-mod-52
  (the reviewer). Guard test asserts the seed fits the cap so a future growth spurt can't re-truncate
  silently. This is a real agent-capability fix: Icarus's curated Godot lessons now actually reach it.

## harness-mod-54 - run tool keeps the END of long output (the error), not the head
- harness/icarus/agent/runtime.py: the `run` tool returned `combined.strip()[:_MAX_OUTPUT]` -- the FIRST
  2000 chars. But a Python traceback's `SomeError: message` and Godot errors are the LAST lines, and
  stderr is appended AFTER stdout, so a command with long stdout cut the actual error off entirely and
  Icarus (whose whole loop is "read the error, fix it") never saw what failed. Now tail-truncates (keeps
  the last _MAX_OUTPUT with a "head truncated" marker) so the error/result always shows. Real debugging-
  capability fix. Regression test: a program printing 5000 chars then raising -> the error survives.

## harness-mod-55 - Strip provenance headers from SFT training outputs
- harness/icarus/distill.py: the SFT `output` was the raw committed module, which starts with the
  "# BUILT BY ICARUS ... autonomy 1.0 ..." provenance header I prepend at commit. Training on that teaches
  a future fine-tune to REPRODUCE that meta-comment atop every solution -- pure noise that would pollute
  the model. Added `_strip_provenance` (drops only the leading contiguous comment block, and only when it
  starts with the provenance marker, so a module's real leading comments survive). Regenerated
  data/onepond_sft.jsonl -> outputs now start with real code (`def ...`). Guard: the wellformedness test
  now asserts no committed SFT output contains the provenance marker. A data-quality fix for the frontier.

## harness-mod-56 - Exclude hardcoded-literal solutions from the SFT corpus
- harness/icarus/distill.py: `is_trivial_hardcode(output)` flags a bare `print(<literal>)` (e.g. print(715),
  print('cunsndc')). These pass the per-instance checker but are POISON as fine-tune data -- they teach a
  coding model to guess/hardcode the answer instead of writing general code. 8 of 82 committed records were
  such literals (incl. a `print(55)` pond-score). ops/generate_training_data.py now rejects them at
  generation; the committed generated_*_sft.jsonl were cleaned (corpus 82 -> 73 higher-quality pairs);
  the wellformedness test guards that none remain. A real data-quality fix for the one open frontier.

## harness-mod-57 - A tool exception is an observation, not an agent crash
- harness/icarus/agent/runtime.py: run_agent called `exec_tool(...)` UNWRAPPED, and `write_file`/`read`/`ls`
  do file ops without try/except -- so a PermissionError (locked file, permissions) / disk-full / any OSError
  propagated out and KILLED the whole agent run. A real battery task (place_n8) crashed exactly this way
  under IO contention. Violates the plan's "a tool failure is an observation, not a crash". Wrapped the
  exec_tool dispatch: any tool exception now becomes a `ToolResult(False, "tool '<name>' errored: ...")` the
  agent reflects on + continues. Uniform (covers every tool, incl. ones without their own try/except).
  Regression test: a tool that raises PermissionError -> the run RETURNS a terminal state, never raises.

## harness-mod-58 - Grow the procedural gym with non-hardcodable input-reading generators (Lever 1)
- harness/icarus/eval/capability.py: added gen_read_max + gen_read_evens (read numbers.txt -> print the max
  / count evens). Like gen_read_sum, the input is written per-instance by setup(), so the answer is UNKNOWN
  at generation and the solution MUST read + compute generally -- it can't be shortcut to print(<literal>)
  (the hardcoding class is_trivial_hardcode filters out). Registered in default_generators (the battery) +
  LOGIC_GENERATORS (the procedural data gym, ops/generate_training_data.py). Grows the gym's breadth with
  HIGH-QUALITY, real-code tasks -> richer, cleaner future SFT data for the fine-tune. Verifier test: a
  general read-and-compute solution passes, a wrong one fails.

## harness-mod-59 - More gym breadth: sorting + text-search input-reading generators
- harness/icarus/eval/capability.py: added gen_read_sorted (read numbers -> print them ascending, a LIST
  output + exact formatting, unlike the scalar read tasks) and gen_grep_count (read words -> count those
  containing a letter, a text-processing domain). Both read a per-instance input file -> non-hardcodable.
  Registered in the battery (now 23 generators) + the procedural gym. Broadens Lever-1 coverage (aggregate /
  filter / sort / search / text) with real-code tasks for cleaner fine-tune data. Verifier test extended.

## harness-mod-60 - Persistence: re-plan when stuck, don't repeat or give up (Bridger's feedback)
- harness/icarus/agent/runtime.py: Bridger's core feedback is that the agent (and I) must be creative +
  STUBBORN at obstacles, not task-switch away. Two changes to the plan->act->reflect loop: (1) the system
  prompt now tells Icarus to diagnose WHY a step failed and try a DIFFERENT approach until it works, and to
  verify before finishing; (2) a re-plan trigger: after >=2 consecutive tool ERRORs, the loop injects a
  [REPLAN] nudge forcing a one-line why + a different approach (different tool/method/angle), instead of
  letting it bang the same wall or finish on a failing state. consecutive_errors resets on any OK.
  Embodies the plan's "re-plan when stuck" (Part 2A). Regression test: two failing tool calls -> the 2nd
  observation carries [REPLAN]; a success resets it.

## harness-mod-61 - Self-verify before finishing (persistence, cont. of mod-60)
- harness/icarus/agent/runtime.py: the loop accepted `finish` even if Icarus never ran/rendered its work,
  undercutting the "verify before finishing" rule mod-60 added to the prompt. Now: if it wrote an artifact
  (write_file) but never used a verification tool (run/render/see), the FIRST finish gets a one-time
  [VERIFY] nudge ("run or render it, read the result, fix errors, then finish") instead of returning DONE;
  a second finish (or if it already verified, or wrote nothing) is accepted. Advisory, never a hard block
  (won't trap a task that legitimately needs no run). Embodies the plan's "self-verifies before it submits"
  (Part 2A). Regression test: write->finish gets nudged once then DONE; write->run->finish is not nudged.

## harness-mod-62 - Salvage a VERIFIED run as DONE, not STUCK (observed on gpt-oss)
- harness/icarus/agent/runtime.py: running the REAL gpt-oss:20b on a scene task, it built + rendered a good
  gate-passing village but then emitted a PROSE summary instead of a `finish` tool call, so the loop hit the
  3-strikes no-tool-block guard and returned STUCK -- dinging the autonomy metric even though the work was
  done + verified (AgentBuilder harvests + gates the artifact regardless). Fix: on that guard, if the agent
  had already VERIFIED (used run/render/see), return DONE (implicit finish) instead of STUCK; only STUCK if
  it never got anywhere. Safe: the gate still decides commit-quality independent of this state. Also nudged
  the no-tool-block message toward `finish`. Regression test: no-tool-block after a render -> DONE; with no
  verification -> STUCK.

## harness-mod-63 - Cue `finish` after a successful verify (observed on gpt-oss)
- harness/icarus/agent/runtime.py: running the real gpt-oss:20b on a scene task TWICE, it built + rendered a
  good gate-passing village both times but never emitted a `finish` tool call -- ending STUCK (prose, run 1)
  then MAX_STEPS (run 2). Root cause: the model doesn't reliably close out after verifying. Fix: after a
  SUCCESSFUL render/run, the observation carries a one-time [DONE?] cue ("if this satisfies the task, emit
  finish now; otherwise keep improving"). Advisory, fires once, doesn't force finishing. Complements mod-61
  (don't finish BEFORE verifying) + mod-62 (salvage verified-then-prose as DONE). Regression test: a
  successful render observation contains [DONE?] exactly once.

## harness-mod-64 - Reject a PLACEHOLDER write body (found in the unaided measurement's empty-output fails)
- harness/icarus/agent/runtime.py: inspecting the clean 12/20=0.60 measurement's failures showed a real
  pattern -- gpt-oss sometimes writes a file whose body is the protocol's `body:` PLACEHOLDER copied
  literally (`granary.py` = `<code>`, `score.py` = `<file contents>`), so the solution runs but prints
  nothing (a whole class of `got ''` empty-output failures). exec_tool's write_file now rejects a body that
  is just a `<...>` token with "that body is a PLACEHOLDER ... write the ACTUAL file contents", forcing a
  real retry instead of silently accepting a do-nothing file. Real one-line code (`print(1)`) is unaffected.
  Regression test: `<code>`/`<file contents>` rejected, real code accepted. Found by the probe-why-it-fails
  method applied to the north-star measurement.
