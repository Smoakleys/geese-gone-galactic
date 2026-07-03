# Autopilot — autonomous build state

This file is the resume point for an unattended build of the GGG harness. Any session (a
budget refresh, a fresh context, a new agent) should read this first and continue the next
unchecked item. The user's standing order: **build all phases without waiting for input**; he
can intervene but it must never be required.

## How to make progress (the loop)
1. `python -m pytest tests/ -q` — confirm the baseline is green before changing anything.
2. Pick the next unchecked phase below; create a branch `phase-N-...`.
3. Build it. Every `harness/` change needs a `harness/HARNESS_CHANGELOG.md` entry.
4. Add/extend tests under `tests/`; keep the suite green.
5. Dogfood: the self-mod validator should approve the change.
6. Commit → push → open PR → merge (all via the GitHub API with stored git creds; `gh` is not
   installed) → `git checkout main` → ff-merge origin/main → delete the branch.
7. Update this file's checklist and `docs/EXECUTION_PLAN.md`, then repeat.

Repo: https://github.com/Smoakleys/geese-gone-galactic — commit authority lives ONLY in
`harness/gatekeeper.py`; never add another commit path.

## Phase checklist
- [x] Phase 0.5 — walking skeleton (PR #1)
- [x] Phase 1 — real cost-tiered check runner: code + CV checks, ratchet metrics (PR #2)
- [x] Phase 2 — reviewers + four teeth: LLM/consensus reviewer, visual gate, plateau, cold
      audit, decision-log flywheel (PR #3)
- [x] Phase 3 — real Icarus builder seam + control surface: `LLMBuilder`, `RunStore`,
      `AutonomousRunner` (auto escape-hatch on plateau, Pause/Stop-aware), stdlib dashboard +
      heartbeat (PR #4).
- [x] Phase 3.5 — text-to-3D `MeshGenerator` seam + `select_generator` (visual-gate-measured)
      + curated-pack fallback; real GPU worker is a drop-in (`harness/gen3d/`) (PR #5).
- [x] Phase 4 — "One Pond" through the harness: authoritative Python game model
      (`game/onepond/`), game checks, ticket set + Icarus client, screenshot seam, and an e2e
      run to full acceptance at autonomy 1.0. Godot/GDScript view is the drop-in behind the
      screenshot seam (PR #6).
- [x] Phase 4.1 — "Geese Gone Galactic" launch mechanic: a `launchpad` building + `launched`
      score in the game model, a certified `onepond_launch_viable` Stage-A check (scoped to
      ponds with a launchpad; catches dead launch infrastructure) that mints an
      `onepond_launched` ratchet floor, and ticket T-POND-04 driven to acceptance at autonomy
      1.0 (4/4). The first flywheel increment authored entirely through the harness (PR #8).
- [x] harness-mod-5 — wire the ratchet **floor gate** into the Gatekeeper: `check_floors` was
      dead code, so the monotonic ratchet was a storage invariant, not a gate. `try_commit` now
      refuses any candidate whose measured metric falls below an established floor (no promotion,
      no commit, floor/artifact untouched), closing the "Ratchet holds" verification item.
      Dogfooded through the self-mod validator (PR #9).
- [x] Stage C in the live pipeline — `DecisionLogReview`/`load_defect_records` were test-only.
      `AutonomousRunner.run_pending` now, after the tickets are done, harvests the builder
      decision logs from the staging trees (`staging_root/<ticket>/decision_log.jsonl`, always
      in `FORBIDDEN_ARTIFACT_NAMES` so never in `game/accepted`), clusters recurring subjective
      defects, and persists `ProposedAdjustment`s to the `RunStore` (`stage_c_proposals`, a new
      snapshot field — existing shape preserved) which the autopilot summary prints. Off the
      critical path; never gates a commit. E2e test proves a defect recurring across tickets
      (>= threshold) yields a proposal through the runner.
- [x] First full flywheel turn — a subjective Stage-B defect made mechanical. Reviewers kept
      rejecting ponds that were legal + solvent yet "read as dead" (a granary buys goose
      capacity but no hatchery ever fills it). New certified `onepond_liveliness` Stage-A check
      (scoped to ponds with a granary; SKIPs bare build-up ponds) fails any pond that hatches
      zero geese over the horizon and mints `onepond_geese_hatched` as a ratchet floor. Tests
      prove the turn: the lifeless pond slips past the pre-flywheel gates but the new check
      rejects it in Stage A, so the reviewer never has to. One Pond still accepts 4/4 at
      autonomy 1.0.
- [x] Liveliness gate driven through real tickets — the granary tickets (T-POND-03/04) now
      carry an `AC_LIVE` acceptance criterion citing `onepond_liveliness`, so the harvested
      check is a demanded live gate, not just certified in isolation. E2e proves a
      `.onepond_geese_hatched` floor is minted during the run; a loop-level test proves the
      gate catches a lifeless in-loop build and drives Icarus to add a hatchery on rework
      before acceptance. Still 4/4 at autonomy 1.0.
- [x] New game mechanic + its own harvested check — **predators**. Foxes (`"predators": n`)
      eat one goose per un-fenced predator per tick; a new `fence` building neutralizes them
      one-for-one. Orthogonal to the existing numerics (predators default 0, so tickets 01–04
      are unchanged). New certified `onepond_predator_safe` check (scoped to ponds that invite
      predators AND hatch geese) fails any whose flock is culled to nothing, minting
      `onepond_geese_protected` as a floor. New ticket T-POND-05 (the complete galactic
      sanctuary: all five building types, fences out two foxes while launching) driven to
      acceptance — One Pond now accepts **5/5 at autonomy 1.0**.
- [x] Sanctuary pond visually gated — the stub renderer now draws the `fence` tile and the
      prowling predators (fox markers in the margin ring), so a hazardous config *looks*
      hazardous. T-POND-05 renders and passes `ReferenceAnchoredScorer` (edge density 0.26,
      within bounds); a test asserts the predator markers actually appear. The Godot+Xvfb
      worker remains the drop-in behind the same seam.
- [x] Visual gate wired into the live Stage-B path — new `OnePondVisualReviewer` (behind the
      `Reviewer` seam) renders each config and runs `ReferenceAnchoredScorer` as the mechanical
      CV floor beneath the subjective reviewer: a config that doesn't read as a real pond is
      blocked before the subjective reviewer is ever consulted; otherwise it delegates. The
      autopilot and the e2e run now use it, so every One Pond acceptance is visually gated end
      to end. Still 5/5 at autonomy 1.0. Real Godot render is the drop-in behind the same
      `ScreenshotWorker` seam.
- [x] Honest flywheel end-to-end — a Stage-C proposal *became* the check that closes it.
      Reviewers repeatedly reject scattered ponds with a subjective `cohesion` defect; the live
      pipeline harvests those decision logs (Stage C) into a `ProposedAdjustment` whose
      `suggested_check_id` is `auto_cohesion_check`; a deterministic `CohesionCheck` authored to
      that exact id certifies (good/bad fixtures) and now gates a scattered layout in Stage A
      that a bare Stage A waved through. The test asserts the join: the id Stage C *proposed*
      equals the id of the check *authored*. One Pond still 5/5 at autonomy 1.0.
- [x] Stage-C proposals surfaced on the dashboard — the read-only control HTML now shows a
      "Stage C — taste→gate proposals" table (suggested check id, occurrences, defect
      signature) plus a KPI count, straight from the `stage_c_proposals` snapshot field, so an
      operator watching the dashboard sees the flywheel's pending suggestions without the console.
- [x] Cold audit wired into the live ops path — the "acceptance is not forever" tooth existed
      and was unit-tested but nothing ran it in ops. The autopilot now runs `cold_audit` after
      every build (mechanical: hashes + certified checks over the committed tree; adversarial: a
      fresh cold visual re-review of the committed bytes) and refuses exit-0 if the audit is
      blocked — a green build with a dirty audit is a failure. The e2e asserts the audit is clean.
- [x] Periodic in-loop cold audits — `AutonomousRunner` gained `audit_every`: every N committed
      tickets it runs a cold audit over what's been accepted so far, and a finding **hard-blocks**
      (STOPs the runner) so nothing is accepted on top of a tree that no longer verifies. Result
      is persisted to the `RunStore` (`audit` field) and shown on the dashboard. An injectable
      `auditor` seam makes the block path deterministically testable. The autopilot defaults to
      `--audit-every 3`.
- [x] Proved the *real* audit path catches corruption end-to-end — a test accepts a ticket,
      corrupts its committed bytes behind the harness's back, accepts a second ticket, and shows
      the real `cold_audit` (no injected seam) catches the first ticket's hash regression on the
      next in-loop audit and STOPs the runner. The tooth is verified, not just wired.
- [x] harness-mod-6 — Stage C tells "no gate" from "gate too lax". `DecisionLogReview.analyze`
      takes optional `existing_check_ids`: a recurring defect whose criterion is already a
      certified check yields a `tighten_rubric` proposal (the gate exists but is too lax) instead
      of a redundant `new_check`; novel criteria still yield `new_check`. `harvest_stage_c` passes
      the registry's certified ids so the live pipeline makes the call automatically. Dogfooded:
      the self-mod validator approves the change (changelog present, certification + regression
      green).
- [x] Proposal `kind` surfaced — the dashboard proposals table and the autopilot summary now
      show each proposal's `kind` (`new_check` vs `tighten_rubric`), so an operator sees at a
      glance whether Stage C wants a missing gate written or an existing gate tightened.
- [x] Acted on a `tighten_rubric` signal — `CohesionCheck`'s compactness gate tightened
      0.25 → 0.5 (the other half of the flywheel: not a new check, an existing one made stricter).
      A layout the old gate passed (compactness 0.33) is now rejected; every shipped ticket
      (≥ 0.7 compact) still passes and the check still certifies. One Pond stays 5/5 at 1.0.
- [x] Ops entrypoint end-to-end test — `scripts/run_onepond_autopilot.py:main` (the program an
      operator actually runs) is now covered by a test that runs it in a throwaway workspace and
      asserts the whole glue holds: arg parsing, certified registry, visual reviewer, run to
      5/5 acceptance, Stage-C harvest, and the post-build cold audit, all the way to a 0 exit
      code (plus an `--audit-every 0` variant). Regressions in the wiring, not just the units,
      are now caught.
- [x] Sixth mechanic — **water access** (a new *spatial pairwise-adjacency* check, distinct from
      cohesion's compactness). A `well` building waters hatcheries within a Manhattan radius; the
      certified `onepond_water_access` check (opt-in: scoped to ponds that sink a well) fails any
      layout with a hatchery stranded from water and mints `onepond_watered_hatcheries` as a
      floor. New ticket T-POND-06 assembles all six building types (the whole pond) with the
      hatchery watered, driven to acceptance — One Pond now accepts **6/6 at autonomy 1.0**.
- [x] Full production-shaped Stage B composed on One Pond: the visual CV floor now wraps a
      multi-model `ConsensusReviewer` (unanimity required, fail-closed) via `--consensus N`, with
      scripted models offline standing in for real ones. A test proves a real pond with agreeing
      models passes but the same pond with a split vote is rejected fail-closed even though the
      visual gate passed. (Further per-increment history lives in `ops/backlog.md`.)

- [x] Toward the real game — **building tiers (T1→T6)**, the tap-to-upgrade core of the vision.
      Each building carries a `tier` (default 1, so all prior configs/tests are unchanged) that
      scales its output *and* up-front cost; placement rejects tiers outside 1..6. The placement
      check mints `onepond_total_tier` (the base's development level) as a monotonic ratchet floor
      so an upgraded base can never regress in tech. New ticket T-POND-07 upgrades a bakery +
      hatchery to T2 and is driven to acceptance — One Pond now **7/7 at autonomy 1.0**.
- [x] Toward the real game — **soldier training** (Training Grounds musters geese→soldiers; `onepond_army_viable`, T-POND-08) and **campaigns** (Command building spends soldiers→victories; `onepond_campaign_viable`, T-POND-09). The vision's hatch→train→campaign military loop now runs end to end through the harness — One Pond **9/9 at autonomy 1.0**, 15 certified checks.

## External-dependency gates (honest status)
- **Godot + Xvfb screenshot** (Phase 0/4): no Godot binary on this box; the screenshot worker
  is behind a seam with a deterministic stub. Real Godot render is a drop-in.
- **GPU text-to-3D** (Phase 3.5): no GPU here; generator is behind a worker seam with a
  curated-pack fallback.
- **Anthropic API** (Phase 2 prod reviewer): `AnthropicChatClient` is lazily imported and used
  only when `ANTHROPIC_API_KEY` is set; the suite runs fully offline with scripted clients.

## Test baseline
As of the hardened-gate + One Pond core build (agent runtime + routing + certified deterministic checks
incl. python_behavior + a real local Stage-B reviewer + nine agent-built game modules):
`python -m pytest tests/ -q` → 281 passed.

## What remains (all external-hardware-gated, seams in place)
- Real Godot binary + Xvfb to swap `GodotXvfbWorker` in for real One Pond screenshots.
- A real GPU host to swap a TRELLIS/Hunyuan worker in behind `harness/gen3d`.
- An `ANTHROPIC_API_KEY` to run the live `AnthropicChatClient` reviewer.
All three are drop-ins behind existing, tested seams; the pipeline runs fully without them.

## Running the control surface (unattended operation)
- Dashboard: `python -m control.dashboard` style entry — `control.dashboard.serve(store_path)`;
  read-only status + `/heartbeat` (phone-pollable) + Start/Stop/Pause.
- Driver: `control.runner.AutonomousRunner` pulls a ticket queue through the loop, beats the
  heartbeat, auto-escalates to the escape hatch on plateau, and never blocks on a human.
