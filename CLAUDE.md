# CLAUDE.md — orientation for the next session

**Project:** GGG v3 — a strict, self-improving **harness** whose real deliverable is a
locally-based game-dev AI ("Icarus"), used to build *Geese Gone Galactic*. The harness, not
the game, is the near-term product.

## Read these first
- `docs/PLAN.md` — the design/architecture (why the harness exists, the anti-complacency teeth).
- `docs/EXECUTION_PLAN.md` — the ordered Phases 0–4 plan and where we are.
- `harness/README.md` — how the structural core fits together.

## Current status
- **Phase 0.5 (walking skeleton) COMPLETE** — governance thesis proven with stub
  builder/reviewer at zero LLM/GPU cost.
- **Phase 1 (real deterministic check runner) COMPLETE** — cost-tiered Stage A with real
  code checks (Python-syntax, JSON) and CV checks (image loadable / min-resolution /
  not-blank, via Pillow); checks emit metrics minted as ratchet floors.
- **Phase 2 (reviewers + four teeth) COMPLETE** — `LLMReviewer` + multi-model
  `ConsensusReviewer` behind a `ChatClient` seam (offline-scripted; Anthropic in prod),
  reference-anchored CV visual gate validated on a labeled set, plateau detection in the loop,
  hard-blocking cold audits, decision-log→new-check flywheel.
- **Phase 3 (real Icarus + control surface) COMPLETE** — `LLMBuilder` behind a
  `GenerationClient` seam; `control/` package with a durable `RunStore`, an `AutonomousRunner`
  (auto escape-hatch on plateau, Pause/Stop-aware), and a stdlib read-only dashboard +
  heartbeat. Runs unattended; intervention optional via Start/Stop/Pause.
- **Phase 3.5 (text-to-3D worker seam) COMPLETE** — `harness/gen3d/` `MeshGenerator` seam,
  curated-pack fallback, visual-gate-measured `select_generator`; real GPU worker is a drop-in.
- **Phase 4 (One Pond through the harness) COMPLETE** — authoritative Python game model
  (`game/onepond/`), game checks, ticket set + Icarus client, screenshot seam, and an e2e run
  driving the ticket set to full acceptance at autonomy rate 1.0. Godot view is the drop-in.
- **80 governance tests pass:** `pip install -r requirements.txt && python -m pytest tests/ -q`.
- **All planned phases (0.5–4) are done in software.** Remaining work is external-hardware
  swaps behind existing seams: real Godot+Xvfb screenshots, a GPU text-to-3D worker, and the
  live Anthropic reviewer key. See `docs/AUTOPILOT.md`.

## The one invariant to preserve
Commit authority lives **only** in `harness/gatekeeper.py`. Builders write to gitignored
staging and have no commit path. Don't add code that commits or writes the protected tree
from anywhere else — that's the whole point.

## Key seams (swap behind these, don't touch the loop)
- Builder: `harness/icarus/builder.py` (`Builder.build(BuildPacket) -> BuildResult`).
- Reviewer: `harness/review/base.py` (`Reviewer.review(ReviewPacket, Ticket) -> Verdict`).
- Checks: `harness/checks/base.py` — a check runs in Stage A only after certifying against
  good/bad fixtures (`harness/checks/registry.py`).

## Conventions
- Harness *core* is stdlib-only on purpose (imports anywhere). `pydantic` is a Phase-1 upgrade.
- Every `harness/` change needs a `harness/HARNESS_CHANGELOG.md` entry (the self-mod validator
  enforces this).
- Suggested next step: **Phase 0** (install Godot, prove the Xvfb screenshot path) or **Phase 1**
  (replace the trivial `non_empty_artifact` check with real code/CV checks + fixtures).
