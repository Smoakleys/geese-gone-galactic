# ICARUS_CHANGELOG — measured capability changes (the plan's Step E)

Every change to Icarus's agent runtime / routing / notebook, with **before→after** on the honest
scorecard. The rule (PLAN Part 4, Step D): keep a change ONLY if the **unaided-on-novel** number rose
(or a domain moved from fail→pass) and variety didn't collapse — else revert. This log is the capability
history; `harness/HARNESS_CHANGELOG.md` is the code-level companion (every `harness/` change needs an entry
there for the self-mod validator).

## Baseline — honest unaided scorecard (docs/SCORECARD.md)
The first honest measurement replaced the old self-graded "100%". Unaided (fast resident model, no
notebook, single attempt) was strong on logic, weak on 3D visuals and multi-step debugging.

## Model routing (ModelRouter / visual_router)
- **Why:** debugging and free-form 3D visuals were failing on the fast model — a model-fit problem, not a
  runtime bug.
- **Change:** route by ticket — fresh logic + templated scenes → fast `gpt-oss:20b`; free-form visual/Godot
  AND debugging → `qwen3:30b`.
- **Before→after:** debugging **2/4 → 4/4**; free-form render **0/3 → 3/3** (routed to the 30B). Kept.

## Scene template (game/godot/scene_template.py) — the speed win
- **Why:** the 30B is 20 GB on a 16 GB card → permanently offloaded (~43 tok/s) → visual builds ~200 s.
  A hardware ceiling (docs/SPEED.md), not fixable by num_ctx.
- **Change:** Icarus writes only `func build(root)` calling tolerant `add_plane`/`add_box`; `compose_scene`
  wraps it with a correct camera + helpers; router sends templated tasks to the FAST resident model.
- **Before→after:** templated scenes **~200 s → ~19 s**, fast model **0/3 → 4/4** on templated render; full
  One Pond backlog commits in ~68 s @ autonomy 1.0. Kept. (compose hardened over 6 real failures.)

## Working-memory trim + keep_alive + step-cap (runtime.py, ollama.py)
- **Why:** the 8 k window drifted on long trajectories; cold reloads cost seconds.
- **Change:** `_trim_context` keeps setup + last 8 exchanges; `keep_alive="30m"`; step-cap 16→10.
- **Before→after:** coherence held on long tasks with no score regression; latency down. Kept (neutral-to-positive).

## Verify-before-finish nudge — REVERTED
- **Why tried:** debugging misses looked like Icarus finishing without editing.
- **Result:** measured, unaided did NOT rise. Reverted per the rule (the real fix was routing). Logged as a
  negative result so it isn't re-tried blindly.

## Deterministic behavioural check (python_behavior, harness-mod-44/45) — a gate lever
- **Why:** a right-formula-wrong-string typo (`'baker'`, `"\n"`) kept PASSING both `python_syntax` and the
  subjective reviewer (OP-6, OP-8). Per the table, "a flaw keeps passing the gate" → add a *checker*.
- **Change:** `PythonBehaviorCheck` runs a ticket's `{module, call, expect}` examples for exact output;
  certified, wired into `default_registry`, carried by every logic ticket.
- **Before→after:** the exact-output whack-a-mole ended — the `'baker'` typo now FAILs Stage A mechanically;
  live-confirmed guaranteeing OP-8 correctness. Kept.

## Real local Stage-B reviewer (OllamaChatClient + default_reviewer)
- **Why:** the offline StubReviewer couldn't catch subjective/structural defects.
- **Change:** fail-closed local reviewer (gpt-oss:20b), fresh-context, default-FAIL.
- **Before→after:** VALIDATED catching a subtle `\n` bug the stub missed (~4 s); now the live default. Kept.

## Current honest north star (2026-07-03)
- **Unaided battery: 10/12 = 0.83** (all game-logic 4/4; misses = one JSON variance + render, which is the
  16 GB model's real 3D ceiling, addressed operationally by the template + routing).
- **Assisted throughput:** full authored backlog **9/9 @ autonomy 1.0** through the hardened gate (capstone).
