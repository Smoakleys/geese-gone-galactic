# CLAUDE.md — orientation for the next session

## ON SESSION START: read `docs/HANDOFF.md` FIRST and continue autonomously (do not wait for a prompt).
That file is the self-resuming contract; this file is background. Only this repo matters — the old
Unity project at `C:\Users\bhump\GeeseGoneGalactic` is abandoned; **ignore it entirely.**

**Project:** GGG v3 — build the game *Geese Gone Galactic* **primarily BY a local agentic AI
("Icarus"), gated by a strict harness.** The harness is the vehicle; **the game Icarus builds is
the destination.** Icarus is the driving force: a **local, model-agnostic** coding agent (Ollama;
the model is a *free variable* — swap/ensemble freely). **You (Claude) author bounded tickets +
gate; Icarus builds. North star = Icarus autonomy rate → 100%; you build ONLY when Icarus can't,
and then you improve Icarus.** Never build the game by hand.

**Engine = GODOT** (3D low-poly, 2.5D iso). **Pond era only — NO rocket/launchpad/eras/military in
the opening.** First slice = "One Pond" (Nest/Bakery/Pond, bread tick, place-a-building), built by
Icarus. NOTE: `game/onepond/` is currently a **python economy TOY** (a drifted stand-in) — do NOT
extend it; it's being replaced by the real Godot slice (see HANDOFF §4–5).

## Read these first
- `docs/HANDOFF.md` — **self-resuming status + next actions (read this first).**
- `docs/catchup/CATCHUP.md` — the true project history + the design decisions (from the grilling).
- `docs/PLAN.md` — the ultraplan design/architecture (harness teeth, Icarus bootstrap, visual gate).
- `harness/README.md` — how the structural core fits together.
- `docs/CHECKS.md` — the current Stage-A gate catalog.

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
- **Flywheel + teeth wired and verified (beyond the base plan):** Stage C harvests recurring
  subjective defects into `new_check`/`tighten_rubric` proposals (both halves demonstrated —
  a harvested `auto_cohesion_check` and a tightened cohesion gate); the visual gate runs live in
  Stage B (`OnePondVisualReviewer`); cold audits run periodically in the loop and hard-block on a
  finding; the self-mod validator approved a real harness change (harness-mod-6). One Pond now
  drives **6 tickets** (six building types: bakery/hatchery/granary/launchpad/fence/well; checks:
  placement, solvency, launch, liveliness, predator-safety, cohesion, water-access) to acceptance
  at autonomy 1.0.
- **112 governance tests pass:** `pip install -r requirements.txt && python -m pytest tests/ -q`.
- **All planned phases (0.5–4) are done in software.** Remaining work is external-hardware
  swaps behind existing seams: real Godot+Xvfb screenshots, a GPU text-to-3D worker, and the
  live Anthropic reviewer key. See `docs/AUTOPILOT.md` (kept current every increment) and
  `docs/HANDOFF.md`.

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
- Next step: read `docs/HANDOFF.md` + `ops/backlog.md` (kept current every increment) and take
  the top backlog item. The software plan is complete; increments now extend One Pond through the
  harness or harden the harness itself. External-hardware swaps (real Godot+Xvfb, GPU text-to-3D,
  live Anthropic key) are drop-ins behind existing tested seams when the hardware/keys appear.
