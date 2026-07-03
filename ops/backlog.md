# Autopilot backlog — next increments (highest value first)

The Stop hook points the agent here every turn. Keep it current: when you finish an
increment, tick it and add the next. This is guidance, not the stop condition — the
ONLY stop condition is the `ops/STOP` kill switch (or Bridger saying stop).

## FOUNDATION COMPLETE (PRs #60-81) — now build BREADTH. See docs/HANDOFF.md.
The agent runtime, AgentBuilder+ModelRouter (visual AND debugging→qwen3:30b, logic→gpt-oss:20b), Godot
rig + certified `godot_parse` + `godot_render` checks, the honest procedural scorecard, and the full
Icarus→gate→committed+rendered pipeline are all built. Use `game/icarus_builder.py:
default_icarus_builder(workdir)` + the full Loop. Each cycle: **1 Icarus ticket + 1 measured harness/
Icarus improvement** (keep only if the unaided battery score rises).

## DONE (PRs #82–105) — the full loop is demonstrated end-to-end
- [x] **Certified `godot_render` gate** + region colour metrics (color_fraction, significant_colors).
- [x] **Bakery + One Pond scenes** via Icarus (routed to the 30B) — land + water + building, gated.
- [x] **One Pond scene committed** (`game/godot/scenes/one_pond.gd`), regression-locked by the gates.
- [x] **Bread tick + placement** built by Icarus and committed (`game/pond/{bread_tick,placement}.py`).
- [x] **Debugging weakness fixed by routing** (30B: 4/4 vs 2/4) — measured; unproven nudge lever reverted.
- [x] **Full pipeline run on authored tickets** (`game/onepond_tickets.py`) → commit @ autonomy 1.0.

## DONE (PRs #107–138) — speed + One Pond core + real reviewer
- [x] **Speed solved** (docs/SPEED.md): 30B is a hardware ceiling; scene TEMPLATE + fast resident model
      builds scenes ~19s; full backlog commits ~68s @ autonomy 1.0. Trim/keep_alive/step-cap shipped.
- [x] **Real LOCAL Stage-B reviewer** (`OllamaChatClient` + `default_reviewer()`), fail-closed, VALIDATED
      catching a subtle bug the stub missed. Lesson: a reviewer only enforces what the criteria state
      (tightened OP-6 AC2 as proof).
- [x] **One Pond core** — six Icarus-built modules `game/pond/{bread_tick,placement,pond_state,predator,
      pond_scene}.py` (+ `game/godot/scenes/one_pond.gd`), composed + tested; OP-1..OP-6 authored.

## DONE (PRs #146–174) — gate hardened, game deepened, mission proven
- [x] **Deterministic behavioural check** (`python_behavior`, harness-mod-44/45): exact-output gating from
      a ticket's `behavior` examples; wired into `default_registry`; on EVERY logic ticket. Ends the
      exact-output whack-a-mole (OP-6 `\n`, OP-8 `'baker'`).
- [x] **`default_reviewer()` is the live default** — the full backlog ran under real review; a bad build
      was reworked (OP-5 in the capstone; the behavioural gate forces pinned criteria on rebuild).
- [x] **CAPSTONE**: full authored backlog committed **9/9 @ autonomy 1.0** through the full gate, unattended.
- [x] **Honest UNAIDED north star measured: 10/12 = 0.83** (all game-logic 4/4; only structural miss is
      complex 3D render on the 16GB-resident model).
- [x] **One Pond deepened to ELEVEN agent-built modules** under a clean `game/pond` API (economy w/ granary
      synergy, placement, sim, predator safety, granary, composed economy, state→scene bridge, status,
      win/lose outcome, water access) + `one_pond_full.gd` with 5 coloured building types.
- [x] **Stale docs truthed-up**: CLAUDE.md (v1→v3), HANDOFF, SCORECARD, SPEED, memory, game/pond/README.
- [x] **Process discipline hardened** after two red-mains: build module FIRST, commit ticket+module+test
      TOGETHER, VERIFY GREEN before merge.

## DONE (PRs #175–200) — battery grown, game to 14 tickets, and a REAL gate bug found + fixed
- [x] **Grew the sealed battery** to cover the full game-logic surface (predator/granary/score/outcome
      generators, harness-mod-46..49) + a battery-integrity meta-test. Unaided-LOGIC measured 11/15 (~0.73,
      variance band 0.73–0.85; all game mechanics in reach).
- [x] **Game deepened to 14 tickets / 13 game/pond modules**: OP-11 water_access, OP-12 pond_score, OP-13
      pond_advice (hints), OP-14 predator_loss (predators with teeth) + a `'dry'` outcome; runnable demo
      (`ops/play_onepond.py`) shows thriving vs predator-drained ponds.
- [x] **CRITICAL FIX (harness-mod-50)**: `python_behavior` was SILENTLY SKIPPED in the live pipeline
      (targets=["*.py"] vs kind-based `_applies`) from harness-mod-45 — a broken module could commit
      (found via OP-14). Fixed, regression-tested through `run_stage_a`, audited all checks (only offender),
      added a guard against the class, and CORRECTED the overstated "behavioural-gate" claims across all
      docs (the reviewer was the real enforcer). See [[ggg-test-checks-through-registry]].

## Now — mission comprehensively proven. AWAITING BRIDGER on the visuals fork (2026-07-03).
- [ ] **VISUALS FORK — Bridger's call (BLOCKED on his decision).** Progress since: visuals deepened from 2
      to FIVE agent-built scenes (goose, flock, world) + a `add_sphere` helper for rounded shapes; unaided
      logic re-measured 13/16 = 0.81 (no regression); reviewer truncation bug fixed (harness-mod-52). HONEST
      FINDING (see memory `ggg-abstract-visuals-fail-judges`): the box/sphere geese do NOT read as geese to
      an independent judge — a text reviewer on the code is inconsistent noise, and the qwen2.5vl vision
      model on the RENDER flatly fails them ("a green square with a blue square and an orange shape"). The
      earlier scene "reviewer passes" were luck, not recognition. So this is not a reviewer bug to hack — the
      real lever is ART. Two honest paths, **Bridger to choose**: (1) real goose-shaped 3D art (proper
      assets / text-to-3D — a big lift on 16GB local), or (2) own the abstract low-poly style and gate scenes
      on the objective checks only (parse/render/colour/layout), dropping the unreliable "looks like a goose"
      subjective bar. Do NOT force a subjective visual pass — that would be faking. If keeping a subjective
      scene gate, route it to the VISION model on the render (plan's see-screenshot), noting even 7B vl is a
      harsh judge of these abstract shapes.
- [ ] **More authored One Pond LOGIC tickets** — each = game content + a verified self-distillation pair;
- [ ] **More authored One Pond LOGIC tickets** — each = game content + a verified self-distillation pair;
      diversity is now good (8 task shapes), so prefer visual/new-domain tickets over more same-shape logic.
- [x] **Retire the python economy toy** (`game/onepond`) — DECIDED: KEEP IT, documented-as-dead. Investigated
      (2026-07-03): its 3 dependent tests are ~914 lines (`test_phase4_onepond` alone is 680) that exercise
      real HARNESS governance — the check registry, flywheel harvest, cold audits, the ratchet — using the
      toy only as a sample artifact. Deleting it would LOSE that coverage. The original motivation (score
      inflation) is MOOT: the scorecard is now the separate unaided battery, not the toy. So retiring is
      net-negative (loses harness coverage, risky migration, zero benefit). It's clearly labelled dead in
      CLAUDE.md + README so it can't mislead; do NOT extend it, but leave it as governance-test scaffolding.
- [x] **Strengthen the OBJECTIVE render gate (plan Lever 2)** — DONE (PR #276). `godot_render` now requires
      >= 3 distinct significant colours (background + land + >=1 element), so a degenerate all-green
      bare-land render FAILS instead of passing on green-dominance alone. Re-anchored the certified good
      fixture to land+pond; certification re-verified (green-on-good, red-on-bad); all 5 committed scenes
      still pass; the e2e render-gate test's own bare-land fixture got a pond; degenerate-render regression
      test added. The honest objective bar, path-independent of the visuals-art decision.
- [ ] **Advance the UNAIDED battery number** (the true north star) — the base-runtime prompt/routing levers
      are largely exhausted (model-limited on the 16GB card). The plan's REAL lever is now BUILT: the
      **self-distillation pipeline** (`harness/icarus/distill.py` + `ops/build_sft.py`, harness-mod-51)
      turns Icarus's gate-passing solutions into QLoRA SFT data (`data/onepond_sft.jsonl`). NEXT (external
      GPU step): QLoRA fine-tune gpt-oss:20b on that data, then re-run the unaided battery and keep the
      adapter ONLY if unaided rises. Grow the dataset two ways, BOTH BUILT: author + build more tickets
      (each adds a verified pair, `ops/build_sft.py`), OR scale via the procedural gym
      (`ops/generate_training_data.py` — runs generated instances through the agent, keeps checker-passing
      solutions; smoke-tested live). Full runbook in `docs/DISTILL.md`. This is the one genuinely-open
      frontier; everything else is comprehensively proven.

## Candidate increments (pick by value, not order)
- [ ] Improve Icarus each cycle (prompt/packet/tooling/**model**-swap or ensemble) toward higher
      first-pass PASS-rate; log in `harness/HARNESS_CHANGELOG.md` / an Icarus-improvements note.
- [ ] Quality hardening: hunt real correctness bugs across `harness/`, `control/`; fix with tests.
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
- [x] Refreshed the stale `harness/README.md` (was "Phase 0.5 walking skeleton" claiming Phases
      2–4 were future): current module map (review sub-modules, audit/, gen3d/, control/) + honest
      "what's still external" section
- [x] Live visual gate is now reference-anchored: committed a canonical pond render; the
      `OnePondVisualReviewer` scores each render against it (histogram similarity), so off-palette
      art is caught — not just blank/tiny/noise. Test proves a structured-but-off-palette render
      is rejected on palette while real ponds pass; still 6/6 (124 tests)
- [x] Guard the load-bearing reference render: test asserts the committed `reference_pond.png` is
      a valid 128x128 non-blank pond image (a bad regeneration is caught, not silently weakening
      the gate) (125 tests)
- [x] Escape-hatch on real One Pond work: Icarus plateaus on an insolvent config (economy check
      fails every round) and the runner auto-escalates to the escape-hatch builder, which ships a
      solvent pond that's accepted — proving "never block on a human" on a real game-quality
      failure through the actual game registry (126 tests)
- [x] Game checks are total functions: a valid-JSON but malformed config (`buildings` not a list
      of dicts) was crashing placement/economy/liveliness/predator/water with an uncaught
      TypeError/AttributeError; now a clean Stage-A FAIL (harness-mod-7 principle for game/) (127)
- [x] harness-mod-8: `run_stage_a` is fail-closed against a check that raises — an unexpected
      exception from any certified check becomes a FAIL (never crashes the loop, never PASSes),
      making the total-function guarantee structural at the runner; self-mod approved (128 tests)
- [x] harness-mod-9: Stage B is fail-closed against a reviewer that raises — a model/network
      failure becomes a blocking review defect (rework/escalate), never crashes the run and never
      passes; runner test proves survival + block; self-mod approved (129 tests)
- [x] harness-mod-10: the builder call is fail-closed too — a generation-client crash discards
      partial output and rejects the empty build (completes the check/reviewer/builder trio: no
      single loop actor can crash the unattended run); self-mod approved (130 tests)
- [x] Orchestration-level net: `AutonomousRunner.run_pending` catches any catastrophic per-ticket
      failure (e.g. an unexpected Gatekeeper/git error the loop doesn't handle), blocks that ticket
      and continues the queue — the run never dies mid-queue (131 tests)
- [x] Email digest notifier (`ops/notify.py`): SMTP+app-password sender (gitignored config,
      console dry-run when absent) + git-based per-session digest (headline, test count, one line
      per change + PR refs) + alert/test/preview CLI; docs/REMOTE_SETUP.md email steps (135 tests)
- [x] Remote control site: dashboard gains token auth (login page + cookie) + a CLI; Start/Stop
      also manage the `ops/STOP`+`AUTOPILOT_ON` sentinels (remote Stop halts the whole system);
      `ops/serve_remote.py` runs it behind a Cloudflare quick tunnel (emails the URL+token);
      docs/REMOTE_SETUP.md §2 (140 tests) — LIVE + verified (email + tunnel), PRs #46–49
- [x] Toward the real game: **building tiers T1→T6** (tap-to-upgrade core of the vision). `tier`
      scales output+cost (default 1 = unchanged); placement gates 1..6 and mints
      `onepond_total_tier` as a progression ratchet floor; T-POND-07 upgrade ticket driven to
      acceptance 7/7 (144 tests)

## Now (toward the real game — see GeeseGoneGalactic/docs/VISION.md)
- [ ] Continue evolving One Pond toward the vision's core loop: soldier-goose training (convert
      geese → soldiers via a training building), then simple campaigns (spend soldiers for a
      reward), then era expansion. Each a mechanic + certified check + ticket to acceptance 1.0.
