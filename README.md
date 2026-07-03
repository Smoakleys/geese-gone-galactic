# Geese Gone Galactic (v3)

A strict, self-improving **harness** that bootstraps a local AI *agent* (**Icarus**, on Ollama) and uses
it to build the game — logic *and* visuals — with every piece held to an un-gameable quality gate.
Engine: **Godot** (3D low-poly, 2.5D fixed iso camera). Pond era only.

**Icarus built a real, playable game.** The "One Pond" core is **28 agent-authored Python modules**
(`game/pond/`) — a granary-synergy bread economy, placement, simulation, predator safety, water access, a
layered win/lose outcome, score + rank progression, a hint system, dynamic events, a goose population,
planning/affordability helpers, a text-command interface, and save/load — composing into a guided game,
plus **five agent-built Godot scenes** (`game/godot/scenes/`, culminating in the complete world with
geese). Every module was produced by the local agent through the gate and is behaviour-locked by a test.
Icarus's gate-passing solutions are also captured as self-distillation training data (`data/*_sft.jsonl`,
see `docs/DISTILL.md`) to raise its unaided capability.

**Try it:** `python ops/play_onepond.py` plays a guided pond to a thriving outcome and prints the transcript.

- Honest capability: the full authored backlog commits **11/11 at autonomy 1.0** through the hardened gate,
  unattended; unaided-logic sits in a ~0.73–0.85 band (see `docs/SCORECARD.md`).
- Read `docs/HANDOFF.md` first (self-resuming status), then `docs/PLAN.md` (architecture),
  `game/pond/README.md` (the game core), `docs/ICARUS_CHANGELOG.md` (measured capability history).

Commit authority lives ONLY in `harness/gatekeeper.py`. The archived Unity v1/v2 lives separately and is
not built upon.
