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

## External-dependency gates (honest status)
- **Godot + Xvfb screenshot** (Phase 0/4): no Godot binary on this box; the screenshot worker
  is behind a seam with a deterministic stub. Real Godot render is a drop-in.
- **GPU text-to-3D** (Phase 3.5): no GPU here; generator is behind a worker seam with a
  curated-pack fallback.
- **Anthropic API** (Phase 2 prod reviewer): `AnthropicChatClient` is lazily imported and used
  only when `ANTHROPIC_API_KEY` is set; the suite runs fully offline with scripted clients.

## Test baseline
As of the visual gate in Stage B: `python -m pytest tests/ -q` → 101 passed.

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
