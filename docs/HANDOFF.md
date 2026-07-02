# HANDOFF — start here (self-resuming)

You are a fresh Claude session on **Geese Gone Galactic (GGG v3)**. Read this file top to bottom
and **continue autonomously — do not wait for a prompt.** `CLAUDE.md` points you here on startup.

> **Scope discipline:** this is the ONLY project. There is an old, abandoned Unity project at
> `C:\Users\bhump\GeeseGoneGalactic` — **ignore it entirely; never read from or build on it.**
> Everything below is about `C:\Users\bhump\geese-gone-galactic` and only this repo.

---

## 1. What this project actually is (the purpose — do not lose it)
Build a genuinely good game — **Geese Gone Galactic** — **primarily BY a local agentic AI called
Icarus**, gated by a strict harness. **The harness is the vehicle; the game Icarus builds is the
destination.** Two things are true at once and both matter:

- **Icarus is the driving force.** Icarus = a **local, model-agnostic coding agent** (Ollama).
  It does the building. **Claude (you) = operator / reviewer / taste authority / harness
  architect + bootstrapper.** You author bounded tickets with pre-committed acceptance criteria;
  Icarus builds them; the gate decides.
- **The north star is Icarus's autonomy rate → 100%** (share of gate-passing work Icarus produced
  with zero Claude building). **You build ONLY when Icarus genuinely can't — and then it's a
  diagnostic: you immediately improve Icarus so next time it can.** The Owner's #1 recurring burn:
  *"I caught you not using Icarus and building GGG by hand."* Do not build the game by hand.

**Icarus is fully malleable — including the model.** Swapping Icarus's model (size, a different
model, an ensemble, fine-tune) is *explicitly acceptable* per the ultraplan. Treat the model as a
free variable: `OllamaGenerationClient(model_id=...)`. Pick the best model per ticket; ensemble if
it helps. Nothing about Icarus is fixed — prompts, packet format, tooling, and the model are all
yours to change (guard-railed by the gates).

## 2. The game (Pond era only — no drift)
Cozy, comedic **goose base-builder**; serious presentation, ridiculous content (Hay Day / Egg Inc
/ Boom Beach). **3D low-poly, presented 2.5D on a fixed iso camera, in GODOT.** Era ladder
Pond → Region → Planet → Galaxy where **space is the ENDGAME, not the start.**
**HARD RULE: the opening is the Pond era only — NO rocket / launchpad / planets / eras / military
in the opening.** (The Owner has repeatedly called this exact drift out: *"why do we have a rocket
yet?"*.) Era is expressed later through building tiers T1→T6.

**First vertical slice = "One Pond":** fixed iso camera, **3 AI-generated low-poly buildings
(Nest, Bakery, Pond)**, a **bread-economy tick**, and **place-a-building** — thin but complete, so
it forces Icarus through code tickets + art tickets + the visual gate at once.

## 3. The operating loop (run this every cycle)
1. **You author one ticket** = a bounded objective + **pre-committed, testable acceptance criteria**
   (no moving goalposts).
2. **Icarus builds it** (`OllamaGenerationClient` behind the builder seam). Route bounded work
   THROUGH Icarus, not by hand.
3. **Gate:** deterministic checks (Godot compiles / scene loads / structural checks) **+ a fresh,
   zero-context, un-steerable reviewer** (adversarial, default-FAIL). Visual artifacts also get a
   reference-anchored visual review.
4. **Gatekeeper commits** only on PASS. **Commit authority lives ONLY in `harness/gatekeeper.py`.**
5. **Bootstrap:** fold one defect you diagnosed by eye into an objective check; **make one concrete
   Icarus improvement each cycle.** Keep the autonomy rate visible and climbing.

**Four anti-complacency teeth (you are bound by them too):** adversarial default-FAIL reviewer,
monotonic quality ratchet (every accept → regression fixture), plateau detection that
auto-escalates, periodic cold-audit red-teams. Never let Icarus *or* yourself coast.

## 4. Current status (2026-07-02)
- **Tests: 159 passing** (`python -m pytest tests/ -q`). Keep green (red = job #1).
- **Harness bones are built and real** (this is the good part): the strict Gatekeeper (sole commit
  authority), fixture-**certified** Stage-A checks, Stage-B reviewer + reference-anchored visual
  gate (`harness/review/`), the monotonic ratchet, guard-railed self-modification (self-mod
  validator + `HARNESS_CHANGELOG.md`), the `AutonomousRunner`, and a token-authed remote control
  dashboard + email digests (`ops/`). All faithful to the ultraplan spec.
- **Icarus is now REAL (PR #58):** `harness/icarus/ollama_client.py` — a local Ollama builder
  behind the `GenerationClient` seam. **Verified live:** it built a correct Godot GDScript from a
  bounded ticket in ~29s. Ollama is up with `qwen3-coder:30b` (default coder), `qwen3:30b`,
  `qwen3:14b`, `qwen3:4b` (fast), and **`qwen2.5vl:7b` (a local VISION model — use it for the
  visual gate)**.
- **The drift being corrected (READ THIS):** the previous long autonomous run turned the harness's
  *proving* game — `game/onepond/` — into an abstract **python economy toy** (bread → geese →
  soldiers → campaigns → eras → **launchpad/rocket** → tiers) with a colored-square "renderer,"
  and it built everything **by hand (scripted stub), never using Icarus, never in Godot.** That is
  NOT the game. It's kept green for now only as a temporary stand-in — **it is being replaced by
  the real Godot One Pond slice built by Icarus, and the military/era/rocket bloat gets pared back
  as we go.** Do not extend the python economy toy.
- **Not yet present:** **Godot is not installed** (needed for the real slice + headless
  screenshots); no Godot project yet; the visual gate hasn't been pointed at a local vision model
  yet. `codex` is not on PATH (prefer the local `qwen2.5vl:7b` for vision per the "free/local" rule).

## 5. Next actions (ordered — just do them, branch → test → PR → merge)
1. **Install Godot** (headless-capable). No admin: download the Godot 4 Windows binary to a
   gitignored `ops/bin/` (same pattern as `ops/bin/cloudflared.exe`) and confirm `--headless
   --version`. Prove a headless scene-load + screenshot path (this is Phase 0 of the plan).
2. **First real Icarus ticket → a Godot artifact.** Author a bounded ticket ("a Godot 4 project
   that opens a fixed 2.5-iso scene showing an empty grassy pond ground; headless run exits 0"),
   route it THROUGH Icarus (`LLMBuilder(OllamaGenerationClient("qwen3-coder:30b"))`), add the
   deterministic check that gates it (godot headless compile/scene-load), drive it to acceptance.
   **This is the first non-toy, Icarus-built, gated commit — the real start.**
3. **Point the visual gate at the local vision model** `qwen2.5vl:7b` (Ollama supports images):
   a reviewer that scores an iso screenshot against the design bar, decomposed + default-NO. Keep
   the existing reference-anchored CV floor beneath it.
4. **Build "One Pond" the real way,** one ticket at a time through Icarus: Nest/Bakery/Pond as
   AI-generated low-poly assets (free/local text/image→3D first, curated fallback) → imported to
   Godot → iso-screenshot → gated; a bread-economy tick; place-a-building. **Each cycle: 1 ticket
   through Icarus + 1 Icarus improvement.**
5. **Retire the python economy toy** as the Godot slice takes over its role (strip
   soldiers/campaigns/eras/launchpad/tiers; keep only what the real Pond-era slice needs), keeping
   tests green.

## 6. Workflow + invariants (unchanged)
- **Every increment: branch → `python -m pytest tests/ -q` green → PR → squash-merge → sync main.**
  GitHub API via `git credential fill` (repo `Smoakleys/geese-gone-galactic`; `gh` not installed).
- **Commit authority ONLY in `harness/gatekeeper.py`.** Every `harness/` change needs a
  `harness/HARNESS_CHANGELOG.md` entry (self-mod validator enforces it); dogfood the validator.
- **Don't stop:** `ops/AUTOPILOT_ON` sentinel + the Stop hook enforce continuation; `ops/STOP` is
  the only kill switch. Keep the site + email fresh: `python ops/status.py "<current activity>"`
  each increment; `python ops/notify.py digest` per session. Remote control: `python
  ops/serve_remote.py` (Cloudflare quick tunnel; token in `ops/dashboard_token.local`).
- **Owner is fully autonomous / never-wait.** Don't stop to ask; make good calls; the Owner
  interjects to redirect. Deep context: `docs/catchup/CATCHUP.md` + `docs/PLAN.md`.
