# HANDOFF — start here (self-resuming)

You are a fresh Claude session on **Geese Gone Galactic (GGG)**. Read this top to bottom and
**continue autonomously — do not wait for a prompt.** `CLAUDE.md` points you here on startup.

> **Scope discipline:** this is the ONLY project. There's an abandoned Unity project at
> `C:\Users\bhump\GeeseGoneGalactic` — **ignore it entirely.** Everything below is
> `C:\Users\bhump\geese-gone-galactic`.

---

## 1. The mission (don't lose it)
Build a genuinely good game — a cozy comedic **goose base-builder** (Godot, 3D low-poly / 2.5D iso,
**Pond era only** — no rocket/military/eras in the opening) — **primarily BY a local agentic AI,
"Icarus,"** gated by a strict harness. **The harness is the vehicle; the game Icarus builds is the
destination.** North star = Icarus's **unaided problem-solving on novel work**, climbing each cycle.
**You (Claude) build up the harness + teach; Icarus builds the game.** Never build the game by hand;
if Icarus genuinely can't do something, do it, document the *approach*, and fold it back into the
harness. See memory [[ggg-v3-icarus-agent-harness]] and [[work-continuously-expand-icarus]].

## 2. What is BUILT (the foundation is complete — 211 tests green)
Icarus is a **real, measured agent**, and the whole loop is proven end-to-end:
- **Agent runtime** (`harness/icarus/agent/`): a plan→act→reflect loop with tools —
  `write_file/read_file/list_files/search/run/see (vision)/render/note (notebook)/finish` — a lean
  working memory + durable notebook, resilient to transient model failures.
- **AgentBuilder** (`harness/icarus/agent_builder.py`): the runtime behind the harness Builder seam,
  with **ModelRouter** — visual/render/Godot tickets route to a **30B (qwen3:30b)**, logic/code to
  fast **gpt-oss:20b**. `game/icarus_builder.py: default_icarus_builder(workdir)` assembles the whole
  thing (routing + render + vision + curated Godot notebook).
- **Godot pipeline**: install-free Godot 4.7 in `ops/bin/`; offscreen Windows screenshot rig
  (`tools/godot_capture/`, `game/godot/capture.py`); certified `godot_parse` check; `green_dominance`
  render check (blank = near-black OR uniform-gray, NOT a valid solid fill — learned the hard way).
- **Honest scorecard** (`harness/icarus/eval/`): procedural, non-memorizable battery
  (arithmetic/strings/config/logic/**bread-economy**/debugging/multi-file/search/**gdscript**/**render**)
  scored UNAIDED. Icarus is strong at code + game LOGIC (economy 3/3), and now renders visuals via routing.
- **The gate is unchanged and authoritative**: certified Stage-A checks, fresh default-FAIL reviewer,
  sole-commit-authority Gatekeeper, monotonic ratchet. **Proven capstone**: Icarus → full gate →
  committed, rendered pond scene.
- **Ops**: control site + `ops/watchdog.py` (emails on staleness) + a **continuation Stop hook**
  (installed in the user settings; forces this loop to keep going). Emails per increment via
  `ops/notify.py iter`. See [[ggg-notify-and-remote-control]].

## 3. Hard-won lessons (internalize these)
- **A bad verifier corrupts the whole loop.** The render gate was wrong THREE times; each was caught by
  *LOOKING at the actual PNG* (Read the image). Always verify a gate against real artifacts before
  trusting a number. Don't blame the model before checking your gate.
- **The visual limit was model SIZE**, not a ceiling — routing to a 30B fixed it. Model is a free variable.
- **Notebooks pollute if shared** — live runs append to a working COPY (`godot_working_notebook`), never
  the curated seed (`game/godot/godot_lessons.md`); promotion back is deliberate curation.

## 4. Next phase = BREADTH (the foundation is done; now build the game)
Drive One Pond for real, **one Icarus ticket per cycle** via `default_icarus_builder` + the full loop:
Nest / Bakery / Pond as scenes (visual → 30B), a bread-economy tick + place-a-building (logic → gpt-oss),
each gated (`godot_parse` + render + economy checks) and committed. **Each cycle: 1 ticket through Icarus
+ 1 concrete harness/Icarus improvement, measured on the battery** (keep only if the unaided score rises).
Retire the drifted python economy toy (`game/onepond/`) as the real Godot slice takes over.

## 5. Workflow + invariants (unchanged)
- Every increment: branch → `python -m pytest tests/ -q` green → PR → squash-merge via GitHub API
  (`git credential fill`; repo `Smoakleys/geese-gone-galactic`; `gh` NOT installed) → sync main.
- Commit authority ONLY in `harness/gatekeeper.py`; every `harness/` change needs a
  `harness/HARNESS_CHANGELOG.md` entry (self-mod validator enforces).
- `python ops/status.py "<activity>"` each increment; `python ops/notify.py iter "<subject>" "<body>"`
  per increment. `ops/AUTOPILOT_ON` on; `ops/STOP` is the only kill switch.
- Don't stop; a summary is never a stopping point.
