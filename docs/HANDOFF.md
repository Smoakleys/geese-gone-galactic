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
- **The gate is authoritative and now HARDENED**: certified Stage-A checks (`python_syntax`, `json`,
  `godot_parse`, `godot_render`, and **`python_behavior`** — deterministic exact-output gating from a
  ticket's `behavior` examples), a **real local Stage-B reviewer** (`game/icarus_builder.py:
  default_reviewer()` = `LLMReviewer(OllamaChatClient)`, fail-closed), sole-commit-authority Gatekeeper,
  monotonic ratchet. **Proven capstone**: Icarus → full gate → committed, rendered pond scene; and
  spec-driven rebuilds where the behavioural check FORCES a pinned requirement before commit.
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
- **One live model run at a time.** The GPU is 16GB — running two live-model tasks concurrently (esp.
  both needing the 30B) thrashes/hangs. Never launch overlapping live probes; finish one before the next.
- **A reviewer only enforces what the criterion PINS.** A local Stage-B reviewer exists now
  (`game/icarus_builder.py: default_reviewer()`, fail-closed) and catches real bugs — but a
  right-formula-but-wrong-string typo (`'baker'` vs `'bakery'`) slips a loose criterion. Author tickets
  with EXACT strings + a concrete input→output example (`fn([...]) == 7`). Durable lever = a deterministic
  behavioural check (deferred). Working net: **VERIFY every module before committing it to `game/pond`.**

## 4. Next phase = BREADTH (foundation done + FAST; now grow the game)
**Speed is solved (docs/SPEED.md).** The 30B is a hardware ceiling (20GB on 16GB), so visuals use a
SCENE TEMPLATE: Icarus writes only `func build(root)` calling `add_plane`/`add_box`, and
`game/godot/scene_template.py: compose_scene` (+ the AgentBuilder `post_build` hook
`materialize_templated_scene`) wraps it with a correct camera on the FAST resident model — real scenes in
~19s, the full One Pond backlog commits in ~68s @ autonomy 1.0. Templated tasks auto-route to `fast`.
**One Pond core is built** by Icarus: `game/onepond_tickets.py` (OP-1 scene + OP-2/3/4 logic) →
`game/pond/{bread_tick,placement,pond_state}.py` + `game/godot/scenes/one_pond.gd`, composed + tested
(test_one_pond_integration).

Drive it forward **one authored Icarus ticket per cycle** via `default_icarus_builder` + the full loop:
add building variety (granary/fence + its rule), a scene that reflects placed buildings, more mechanics —
each gated + committed. Keep any harness/Icarus change only if it's a measured win (the plan's rule).
Still to do: retire the legacy `game/onepond/` python toy (marked legacy; the real slice is `game/pond`
+ `game/godot`).

## 5. Workflow + invariants (unchanged)
- Every increment: branch → `python -m pytest tests/ -q` green → PR → squash-merge via GitHub API
  (`git credential fill`; repo `Smoakleys/geese-gone-galactic`; `gh` NOT installed) → sync main.
- Commit authority ONLY in `harness/gatekeeper.py`; every `harness/` change needs a
  `harness/HARNESS_CHANGELOG.md` entry (self-mod validator enforces).
- `python ops/status.py "<activity>"` each increment; `python ops/notify.py iter "<subject>" "<body>"`
  per increment. `ops/AUTOPILOT_ON` on; `ops/STOP` is the only kill switch.
- Don't stop; a summary is never a stopping point.
