# Autopilot backlog — next increments (highest value first)

The Stop hook points the agent here every turn. Keep it current: when you finish an
increment, tick it and add the next. This is guidance, not the stop condition — the
ONLY stop condition is the `ops/STOP` kill switch (or Bridger saying stop).

## Now
- [ ] **Extend One Pond further** — a 7th mechanic, a second harvested check via Stage C, or a
      new deterministic check for a different failure mode, driven to acceptance at autonomy 1.0.

## Candidate increments (pick by value, not order)
- [ ] Extend One Pond through the harness: a 4th mechanic, more tickets, a new
      harvested check. Drive to acceptance at autonomy 1.0.
- [ ] Quality hardening: hunt real correctness bugs across `harness/`, `control/`,
      `game/`; fix with tests (high-confidence work only).
- [ ] External drop-ins IF hardware/keys appear: real Godot+Xvfb (`GodotXvfbWorker`),
      GPU text-to-3D worker (`harness/gen3d`), live `AnthropicChatClient`
      (`ANTHROPIC_API_KEY`). Each is a drop-in behind an existing tested seam.

## Done this session
- [x] Phase 4.1 launch mechanic (PR #8)
- [x] harness-mod-5 ratchet floor gate (PR #9)
- [x] docs sync (PR #10)
- [x] anti-stop enforcement: Stop hook + sentinels + external driver (this PR)
- [x] Stage C wired into the live pipeline: runner harvests staging decision logs after
      run_pending, persists `stage_c_proposals` to the store, autopilot prints them; e2e
      test proves a recurring cross-ticket defect yields a proposal (89 tests)
- [x] First full flywheel turn: `onepond_liveliness` check makes the subjective "lifeless
      pond" (granary capacity, no hatched geese) defect a mechanical Stage-A gate; certified
      w/ good+bad fixtures, tests prove it closes the gap, 4/4 still green (94 tests)
- [x] Liveliness gate driven through real tickets: T-POND-03/04 carry an `AC_LIVE` criterion
      citing `onepond_liveliness`; e2e mints a `.onepond_geese_hatched` floor and a loop test
      proves the gate forces rework (Icarus adds a hatchery) before acceptance (95 tests)
- [x] New predator mechanic + `onepond_predator_safe` check: foxes eat un-fenced geese, a
      new `fence` building protects them; T-POND-05 (all five building types) fences out two
      foxes while launching, driven to acceptance 5/5 at autonomy 1.0 (98 tests)
- [x] Sanctuary visual gate: stub renderer draws fences + prowling predators; T-POND-05
      renders and passes `ReferenceAnchoredScorer`; test asserts predator markers appear (99 tests)
- [x] Visual gate wired into live Stage B: `OnePondVisualReviewer` renders each config and runs
      the CV scorer as the mechanical floor beneath the subjective reviewer; autopilot + e2e use
      it, so every acceptance is visually gated; blocks unreadable ponds first (101 tests)
- [x] Honest flywheel end-to-end: recurring subjective `cohesion` defect → Stage C proposes
      `auto_cohesion_check` → `CohesionCheck` authored with that exact id, certified, now gates
      scattered layouts a bare Stage A passed; test asserts proposed-id == authored-id (102 tests)
- [x] Stage-C proposals surfaced on the dashboard: new taste→gate proposals table + KPI count
      from the `stage_c_proposals` snapshot; tests cover empty + populated render (103 tests)
- [x] Cold audit wired into live ops: autopilot re-verifies the committed tree (mechanical +
      cold visual re-review) after every build and fails exit-0 on any finding; e2e asserts clean
- [x] Periodic in-loop cold audits: runner `audit_every` re-audits every N committed tickets and
      hard-blocks (STOPs) on a finding; persisted to store + shown on dashboard; injectable
      `auditor` seam; autopilot defaults `--audit-every 3` (105 tests)
- [x] Proved the real cold_audit path (no injected seam) catches a corrupted accepted artifact
      mid-run and STOPs the runner (106 tests)
- [x] harness-mod-6: Stage C `analyze` distinguishes `tighten_rubric` (criterion already a
      certified check → gate too lax) from `new_check` (novel criterion); runner passes certified
      ids; self-mod validator approves the change (108 tests)
- [x] Proposal `kind` surfaced on the dashboard table + autopilot summary (108 tests)
- [x] Acted on a `tighten_rubric` signal: `CohesionCheck` compactness gate tightened 0.25→0.5;
      previously-passing 0.33 layout now rejected, all tickets (≥0.7) still pass, cert green (109)
- [x] Ops entrypoint e2e test: runs `run_onepond_autopilot.main` in a throwaway workspace to a
      0 exit code (5/5, clean audit); covers the glue the unit tests miss (111 tests)
- [x] Sixth mechanic — water access: `well` building + certified `onepond_water_access` spatial
      pairwise-adjacency check (opt-in on well presence); T-POND-06 (all six building types)
      driven to acceptance 6/6 at autonomy 1.0 (112 tests)
- [x] Doc-sync: refreshed the stale top-level orientation docs (`CLAUDE.md` current-status,
      `docs/EXECUTION_PLAN.md` status callout) to reflect 112 tests, One Pond 6/6, and the
      wired+verified flywheel/teeth — so the next session isn't misled by "80 tests / phases 0.5-4"
- [x] Correctness fix: `harvest_stage_c` now scopes to tickets processed this run (not a glob of
      all staging dirs), so a persistent `--workdir` no longer re-harvests stale prior-run
      decision logs into phantom proposals; test proves stale staging is ignored (113 tests)
- [x] harness-mod-7: deterministic code checks are total functions — a non-UTF-8 or null-byte
      file is a clean Stage-A FAIL, never an uncaught exception crashing the loop (matches the CV
      checks' posture); self-mod validator approved (114 tests)
- [x] Resource hygiene: `OnePondVisualReviewer` creates its render dir lazily (was `mkdtemp` in
      `__init__`, leaking a temp dir per instantiation even when unused) (115 tests)
- [x] `docs/CHECKS.md` — reference catalog of all 13 certified Stage-A checks (tier, scope, what
      each gates, metric→floor) + the Stage-C flywheel; linked from CLAUDE.md; verified vs registry
- [x] `scripts/lint_onepond.py` — dry-run a pond config through the certified Stage-A registry
      (per-check PASS/FAIL/SKIP + evidence, exit 0/1/2); operator/debug tool, no build (119 tests)
- [x] Full production-shaped Stage B composed on One Pond: visual CV floor now wraps a multi-model
      `ConsensusReviewer` (`--consensus N`, scripted offline). Test proves agreeing models pass but
      a split vote is rejected fail-closed even with the visual gate passing; 6/6 with `--consensus 3`
      (120 tests)
- [x] Ratchet floors surfaced on the dashboard: runner mirrors `gatekeeper.ratchet.floors()` into
      the `RunStore` snapshot (new `floors` field) and the read-only HTML shows them + a KPI count
      — the quality-never-regresses record is now visible to an operator (122 tests)
- [x] Full-stack ops e2e: runs the real entrypoint with `--consensus 2 --audit-every 2` — all 13
      checks + visual+consensus Stage B + periodic & post-build cold audits + Stage-C + floors —
      to a 0 exit code, 6/6 clean (123 tests)
