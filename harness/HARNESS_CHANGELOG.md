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
