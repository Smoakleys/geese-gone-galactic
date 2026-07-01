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
- [ ] Phase 3.5 — text-to-3D generator behind a swappable GPU-worker seam (GPU-gated: build
      the seam + a stub/curated-pack worker; real GPU worker is drop-in).
- [ ] Phase 4 — "One Pond" built through the harness in Godot (Godot-gated: build the
      harness-side ticket set, rubrics, reference art hooks, and everything not requiring a
      Godot binary; leave a clear seam for the GDScript/screenshot step).

## External-dependency gates (honest status)
- **Godot + Xvfb screenshot** (Phase 0/4): no Godot binary on this box; the screenshot worker
  is behind a seam with a deterministic stub. Real Godot render is a drop-in.
- **GPU text-to-3D** (Phase 3.5): no GPU here; generator is behind a worker seam with a
  curated-pack fallback.
- **Anthropic API** (Phase 2 prod reviewer): `AnthropicChatClient` is lazily imported and used
  only when `ANTHROPIC_API_KEY` is set; the suite runs fully offline with scripted clients.

## Test baseline
As of Phase 3: `python -m pytest tests/ -q` → 63 passed.

## Running the control surface (unattended operation)
- Dashboard: `python -m control.dashboard` style entry — `control.dashboard.serve(store_path)`;
  read-only status + `/heartbeat` (phone-pollable) + Start/Stop/Pause.
- Driver: `control.runner.AutonomousRunner` pulls a ticket queue through the loop, beats the
  heartbeat, auto-escalates to the escape hatch on plateau, and never blocks on a human.
