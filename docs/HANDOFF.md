# HANDOFF — resume here (autonomous)

You are a fresh Claude Code session that was just restarted (`/clear`) to re-establish remote
connect. **You are mid-way through an autonomous mandate. Do not wait for the user — keep
working.** The user (Bridger) is away ~12h and explicitly ordered: "Under no circumstance are
you to wait for me for anything. Keep going." Neither you nor Icarus may ask him for help.

## First actions on resume
1. `cd C:\Users\bhump\geese-gone-galactic`
2. `python -m pytest tests/ -q` → expect **119 passed**. If red, fixing that is job #1.
3. Read `docs/AUTOPILOT.md` (the phase state + loop) and your memory index `MEMORY.md`
   (`ggg-autonomous-mandate`, `ggg-progress`).

## Where things stand (all merged to `main`)
Repo: https://github.com/Smoakleys/geese-gone-galactic (remote `origin` is set; push/PR/merge
via the GitHub API using stored git creds — `gh` CLI is NOT installed).

- Phases 0.5 → 4 are **COMPLETE**, plus an ops entrypoint, the first flywheel increment
  (Phase 4.1: the "Geese Gone Galactic" launch mechanic — `launchpad` building, certified
  `onepond_launch_viable` check minting an `onepond_launched` ratchet floor, ticket T-POND-04
  driven to acceptance at autonomy 1.0), and harness-mod-5 (the ratchet **floor gate**:
  `Gatekeeper.try_commit` now refuses any candidate that regresses below an established floor —
  `check_floors` was previously dead code). PRs #1–#9 merged. 89 tests green.
- **Stage C is now wired into the live pipeline** (was test-only): after `run_pending`,
  `AutonomousRunner.harvest_stage_c` mines the builder decision logs left in the staging trees
  for recurring subjective defects and persists `ProposedAdjustment`s to the `RunStore`
  (`stage_c_proposals` snapshot field); the autopilot summary prints them. Off the critical
  path — it never gates a commit.
- **First full flywheel turn done:** the subjective "lifeless pond" Stage-B defect is now a
  mechanical Stage-A gate (`onepond_liveliness` in `game/onepond/checks.py`, certified against
  good/bad fixtures, scoped to ponds with a granary; mints `onepond_geese_hatched` floor).
  Tests prove a lifeless pond slips past the pre-flywheel gates but is rejected once the check
  is registered. One Pond still accepts 4/4 at autonomy 1.0.
- **Liveliness gate is now a demanded live gate:** T-POND-03/04 carry an `AC_LIVE` criterion
  citing `onepond_liveliness`; the e2e mints a `.onepond_geese_hatched` floor and a loop test
  proves the gate forces rework (Icarus adds a hatchery) before acceptance.
- **New predator mechanic:** foxes (`"predators": n` in the config) eat one goose per un-fenced
  predator per tick; a new `fence` building neutralizes them one-for-one. It's opt-in (default
  0), so tickets 01–04 are unchanged. New certified `onepond_predator_safe` check mints an
  `onepond_geese_protected` floor. T-POND-05 (all five building types — the galactic sanctuary)
  is driven to acceptance: One Pond now accepts **5/5 at autonomy 1.0**.
- **Sanctuary pond is visually gated:** the stub renderer draws the `fence` tile and prowling
  predator markers; T-POND-05 renders and passes `ReferenceAnchoredScorer`.
- **Visual gate is now live in Stage B:** `OnePondVisualReviewer` (game/onepond/review.py)
  renders each config and runs the CV scorer as the mechanical floor beneath the subjective
  reviewer — unreadable ponds are blocked before the subjective reviewer is consulted. The
  autopilot and the e2e run use it, so every One Pond acceptance is visually gated end to end.
  Still 5/5 at autonomy 1.0.
- **Honest flywheel closed end-to-end:** reviewers' recurring subjective `cohesion` defect is
  harvested by Stage C into a proposal whose `suggested_check_id` is `auto_cohesion_check`; a
  `CohesionCheck` authored with that exact id certifies and now gates scattered layouts a bare
  Stage A passed. The test asserts proposed-id == authored-id — the full unattended taste→gate
  loop, not a hand-picked check.
- **Stage-C proposals are visible on the dashboard:** the read-only control HTML shows a
  "Stage C — taste→gate proposals" table + a KPI count from the `stage_c_proposals` snapshot.
- **Cold audit is wired into ops:** the autopilot runs `cold_audit` after every build
  (mechanical hashes+checks over the committed tree, plus a fresh cold visual re-review) and
  refuses exit-0 if it's blocked; the e2e asserts a clean audit.
- **Periodic in-loop cold audits:** `AutonomousRunner.audit_every` re-audits every N committed
  tickets and hard-blocks (STOPs the runner, persists to `store.audit`, shows on the dashboard)
  on any finding, so nothing is accepted on top of a tree that no longer verifies. Injectable
  `auditor` seam; autopilot defaults `--audit-every 3`. The *real* audit path is verified end
  to end: a test corrupts a committed artifact behind the harness's back and shows the next
  in-loop `cold_audit` catches the hash regression and STOPs the runner.
- **harness-mod-6 (first harness/ change this session):** Stage C's `DecisionLogReview.analyze`
  now distinguishes `tighten_rubric` (the recurring defect's criterion is already a certified
  check → the gate is too lax) from `new_check` (novel criterion), via an optional
  `existing_check_ids` arg that `harvest_stage_c` fills from the registry. Dogfooded — the
  self-mod validator approves it. The proposal `kind` (`new_check`/`tighten_rubric`) is shown on
  the dashboard table and autopilot summary. Both halves of the flywheel are now demonstrated:
  a `new_check` harvested from a proposal (cohesion) AND a `tighten_rubric` acted on (the same
  cohesion gate tightened 0.25→0.5).
- **Ops entrypoint is now e2e-tested:** `run_onepond_autopilot.main` runs in a throwaway
  workspace to a 0 exit code, covering the glue the unit tests miss.
- **Sixth mechanic — water access:** a `well` building waters hatcheries within a Manhattan
  radius; the certified `onepond_water_access` check (opt-in on well presence) is a new *spatial
  pairwise-adjacency* shape distinct from cohesion. T-POND-06 assembles all six building types
  and is driven to acceptance: One Pond now accepts **6/6 at autonomy 1.0**. Next: extend One
  Pond further, or another high-value increment (see `ops/backlog.md`).
- The harness runs unattended: `python scripts/run_onepond_autopilot.py` (add `--serve` for the
  dashboard). Verified to make real Gatekeeper commits at 100% autonomy.

## The workflow (follow it every time)
1. `python -m pytest tests/ -q` green before starting.
2. New branch `phase-…`/`feat-…`; build; add tests; keep the suite green.
3. Every `harness/` change needs a `harness/HARNESS_CHANGELOG.md` entry (self-mod validator
   enforces it). Dogfood: the self-mod validator should approve the change.
4. Commit → push → open PR → merge → `git checkout main` → ff-merge origin/main → delete branch.
   Use the GitHub API (`curl` + token from `git credential fill`), same as prior PRs.
5. Update `docs/AUTOPILOT.md` + `docs/EXECUTION_PLAN.md` + this file's status, then repeat.

**The one invariant:** commit authority lives ONLY in `harness/gatekeeper.py`. Never add
another commit path.

## What to do next (pick the highest-value; never make-work)
1. **Quality hardening** — hunt real correctness bugs across `harness/`, `control/`, `game/`;
   fix with tests. High confidence work.
2. **Extend One Pond through the harness** (the intended flywheel) — e.g. a 4th building, a
   "launch geese to space" scoring mechanic, or a new deterministic check harvested from a
   recurring Stage-B defect (`decision_log_review`). Author it as tickets and drive it through
   `AutonomousRunner` to acceptance. This exercises the system doing its real job.
3. **External drop-ins** — only if the user has provided them: real Godot+Xvfb
   (`GodotXvfbWorker`), a GPU text-to-3D worker (`harness/gen3d`), or `ANTHROPIC_API_KEY` for
   the live `AnthropicChatClient` reviewer. Each is a drop-in behind an existing tested seam.

## Remote-connect note
This restart was performed to fix a dropped remote-connect link (`remoteControlAtStartup: true`
is already set in `~/.claude/settings.json`). If remote connect still isn't working after this
fresh session, a full `claude` process relaunch may be needed — but do not stop the build over
it; all progress is durable on GitHub and in these docs.

## Keep going
After you finish an increment, start the next one. Update this handoff before any future
restart. The measure of success is that the system (and you) keep running without the user.
