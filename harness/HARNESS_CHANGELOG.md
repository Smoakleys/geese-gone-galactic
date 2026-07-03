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
