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

## Deterministic behavioural check (python_behavior, harness-mod-44/45; genuinely wired harness-mod-50)
- **Why:** a right-formula-wrong-string typo (`'baker'`, `"\n"`) kept PASSING both `python_syntax` and the
  subjective reviewer (OP-6, OP-8). Per the table, "a flaw keeps passing the gate" → add a *checker*.
- **Change:** `PythonBehaviorCheck` runs a ticket's `{module, call, expect}` examples for exact output;
  certified, registered in `default_registry`, carried by every logic ticket.
- **Before→after + HONEST CORRECTION:** the check works and is certified, BUT it declared `targets=["*.py"]`
  while `registry._applies` matches `targets` against `ticket.kind` — so it was SILENTLY SKIPPED in every
  live Stage-A run from harness-mod-45 until **harness-mod-50** fixed it to `["*"]`. My earlier "FAILs Stage
  A mechanically; live-confirmed guaranteeing OP-8" was WRONG for that window: the **reviewer** was the real
  enforcer. Post-fix it genuinely gates (regression-tested through `run_stage_a`). Lesson: test a check
  through the registry path, not just `check.run()` directly. Found via an OP-14 build that committed a
  module raising `AttributeError` on its own examples.

## Real local Stage-B reviewer (OllamaChatClient + default_reviewer)
- **Why:** the offline StubReviewer couldn't catch subjective/structural defects.
- **Change:** fail-closed local reviewer (gpt-oss:20b), fresh-context, default-FAIL.
- **Before→after:** VALIDATED catching a subtle `\n` bug the stub missed (~4 s); now the live default. Kept.

## Current honest north star (2026-07-03)
- **Unaided battery: 10/12 = 0.83** (all game-logic 4/4; misses = one JSON variance + render, which is the
  16 GB model's real 3D ceiling, addressed operationally by the template + routing).
- **Assisted throughput:** full authored backlog **9/9 @ autonomy 1.0** through the hardened gate (capstone).

## Self-distillation data pipeline BUILT (harness-mod-51 + ops/, 2026-07-03) — Levers 1, 3, 5
- **Why:** unaided capability (~0.73–0.85) is model-limited on the 16 GB card; base-runtime levers
  (prompt/routing/step-cap) are exhausted. The plan's real lever to move it is TRAINING on gate-passing data.
- **Built (both data paths):** `harness/icarus/distill.py` + `ops/build_sft.py` distil Icarus's authored-
  ticket successes (22 diverse verified pairs, `data/onepond_sft.jsonl`); `ops/generate_training_data.py`
  scales via the procedural gym (run generated instances through the agent, keep checker-passing solutions —
  smoke-tested live 2/2). Data is verified by construction + quality-guarded (`tests/test_distill.py`).
- **Before→after:** no capability number yet — the QLoRA fine-tune is an EXTERNAL GPU step (full runbook in
  `docs/DISTILL.md`). This entry records the LEVER as built + operational; the before→after will be the
  unaided-battery delta after the first fine-tune (keep the adapter ONLY if it rises). Kept (infrastructure).
