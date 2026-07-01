# HANDOFF — resume here (autonomous)

You are a fresh Claude Code session that was just restarted (`/clear`) to re-establish remote
connect. **You are mid-way through an autonomous mandate. Do not wait for the user — keep
working.** The user (Bridger) is away ~12h and explicitly ordered: "Under no circumstance are
you to wait for me for anything. Keep going." Neither you nor Icarus may ask him for help.

## First actions on resume
1. `cd C:\Users\bhump\geese-gone-galactic`
2. `python -m pytest tests/ -q` → expect **85 passed**. If red, fixing that is job #1.
3. Read `docs/AUTOPILOT.md` (the phase state + loop) and your memory index `MEMORY.md`
   (`ggg-autonomous-mandate`, `ggg-progress`).

## Where things stand (all merged to `main`)
Repo: https://github.com/Smoakleys/geese-gone-galactic (remote `origin` is set; push/PR/merge
via the GitHub API using stored git creds — `gh` CLI is NOT installed).

- Phases 0.5 → 4 are **COMPLETE**, plus an ops entrypoint and the first flywheel increment
  (Phase 4.1: the "Geese Gone Galactic" launch mechanic — `launchpad` building, certified
  `onepond_launch_viable` check minting an `onepond_launched` ratchet floor, ticket T-POND-04
  driven to acceptance at autonomy 1.0). PRs #1–#8 merged. 85 tests green.
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
