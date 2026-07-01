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
