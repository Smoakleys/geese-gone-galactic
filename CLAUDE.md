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

## Current status — v3 (Icarus agent, Pond era). READ docs/HANDOFF.md + docs/SCORECARD.md for live detail.
The v1 governance skeleton below is DONE and archived; v3 built a real local *agent* and forged a real
game with it. Where things stand:
- **Icarus is a real agentic runtime** (`harness/icarus/agent/`): a plan→act→reflect loop with tools
  (write/read/run/search/see-screenshot/render/notebook/finish), resilient parsing, working-memory trim.
  `game/icarus_builder.py: default_icarus_builder()` wires model-routing (fast **gpt-oss:20b** for logic +
  templated scenes; **qwen3:30b** for free-form visuals/debug) + a curated notebook + the render bridge.
- **The gate is HARDENED** (`harness/checks/`): certified deterministic Stage-A checks — `python_syntax`,
  `json_valid`, `godot_parse`, `godot_render`, and **`python_behavior`** (exact-output gating from a
  ticket's `behavior` examples) — plus a **real local Stage-B reviewer** (`default_reviewer()` =
  `LLMReviewer(OllamaChatClient)`, fail-closed). Commit authority still ONLY in `harness/gatekeeper.py`.
- **One Pond is a real, playable game core built BY Icarus**: ten agent-built modules under a clean
  `game/pond` API (economy w/ granary synergy, placement, sim, predator safety, granary, composed
  economy, state→scene bridge, status, win/lose outcome) + rendered Godot scenes (`game/godot/scenes/`).
  Every module is behaviour-locked by a test; integration tests drive place→tick→status→outcome→render.
- **CAPSTONE**: the entire authored backlog (`game/onepond_tickets.py` OP-1..OP-9) committed **9/9 at
  autonomy 1.0 in ~8 min, unattended** through the full gate. Honest UNAIDED north star = **10/12 = 0.83**
  (all game-logic 4/4; only structural miss is complex 3D render on the 16GB-resident model).
- **Speed solved**: the scene TEMPLATE (`game/godot/scene_template.py`) lets the fast resident model build
  scenes ~19s instead of the offloaded 30B ~200s (see docs/SPEED.md). One live model run at a time (16GB).
- **~287 tests pass:** `pip install -r requirements.txt && python -m pytest tests/ -q`.
- **`game/onepond/` is the DEAD v1 python toy** (launchpad/military drift) — superseded by `game/pond`,
  kept only because a few v1 governance tests (flywheel/phase4) still use it as a sample artifact. Do NOT
  extend it. The v1 bullets that used to live here (Phases 0.5–4, 112 tests, 6 military building types)
  described that toy and are archived in git history + the memory index.

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
