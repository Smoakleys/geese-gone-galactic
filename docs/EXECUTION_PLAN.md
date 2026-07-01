# Executable Plan: GGG v3 Harness (Phases 0–4)

> Companion to `docs/PLAN.md` (the design/architecture doc). This is the *ordered,
> executable* plan. **Phase 0.5 is already implemented** (see `harness/` + `tests/`,
> 20 governance tests green); everything from Phase 0 (env) and Phase 1 onward is pending.

## Context

`docs/PLAN.md` is the design doc for GGG v3 — a strict, self-improving harness whose real
deliverable is a locally-based game-dev AI ("Icarus"), bootstrapped until it can build a
genuinely great Geese Gone Galactic. Prior iterations failed because *nothing structural made
bad work or coasting impossible* — the builder self-approved, the visual gate was blind,
quality silently regressed. This plan front-loads the structural core (the hard gate) and the
two highest external risks (Godot headless-screenshot path; local text-to-3D + GPU) so
feasibility is proven before anything is built on top. The deliverable is the harness; the
game ("One Pond") is Phase 4 and exists to prove the harness works end-to-end.

## The one decision that makes the harness real: a Gatekeeper owns commit authority

**No agent — not Icarus, not escape-hatch Claude — ever runs `git commit` or writes to the
protected tree.** Builders write only to a gitignored staging area; a separate **Gatekeeper**
is the *only* code path with commit authority, and it commits *only* after an independent
reviewer's `Verdict` attests PASS. This converts "the prompt tells the builder not to
self-approve" into "the builder has no code path to approve." (Implemented:
`harness/gatekeeper.py`.)

## Stack decision

**Python** for the entire structural core + CV + art; **GDScript** for the game (Godot
mandates it); a thin, read-only dashboard (FastAPI + HTMX) off the critical path. Rationale:
the two least-optional pieces — CV checks and local PyTorch text-to-3D (Hunyuan3D/TRELLIS) —
force Python, and the Gatekeeper↔checks↔builder path must be tight/transactional, so a
cross-language boundary isn't worth dashboard polish. Use `pydantic` (Phase 1+) to recover
type-safety on the `Ticket`/`Verdict`/`BuildPacket` schemas; the walking skeleton is
deliberately stdlib-only so the core imports anywhere.

## Critical external-dependency findings (resolve in Phase 0)

1. **Godot `--headless` disables ALL rendering** — no screenshots in true headless mode. The
   iso-screenshot gate must run Godot under a **virtual framebuffer (Xvfb)** with a
   software/real display driver (or Movie Maker mode under Xvfb). Biggest Phase-0 unknown;
   prove it before designing the visual gate.
2. **Local text-to-3D is GPU-bound.** TRELLIS.2-4B and Hunyuan3D are PyTorch/CUDA. Put the
   generator behind a **swappable worker seam** (remote GPU host now, local later, paid API
   as fallback). Spike to measure quality before committing; fallback is curated low-poly
   packs.

## Structural-core architecture (implemented in Phase 0.5)

- **Data model** (`harness/models.py`): `Ticket` with ordered, independently-testable
  `acceptance_criteria[]` and a **`criteria_hash`** frozen before the build (Gatekeeper
  recomputes and aborts as tampered on any post-freeze edit). `Verdict` is **default-FAIL**:
  PASS requires explicit non-empty evidence on every stage-relevant criterion. Decision log is
  written by the builder but never handed to the Stage-B reviewer.
- **State machine** (`harness/states.py`): the only edge into `COMMIT_PENDING` is
  `STAGE_B_PASS`; `DONE` is unreachable except through `COMMIT_PENDING`; the Gatekeeper solely
  owns `COMMIT_PENDING→RATCHET→DONE`. Escape-hatch Claude builds re-enter at `BUILDING→Stage A`
  like Icarus.
- **Check runner** (`harness/checks/`): a check enters Stage A only after **certification** —
  green on every good fixture AND red on every bad fixture — recorded in `registry.lock`. A
  broken new check is inert. Subjective defects caught by review get folded into new
  deterministic checks over time (taste→gate flywheel).
- **Ratchet** (`harness/ratchet.py`): every accepted artifact becomes a regression fixture;
  numeric floors only rise (`floor = max(old, new)`). Lowering a floor is a distinct, loud,
  logged `baseline_reset`.
- **Reviewer isolation** (`harness/review/packet_builder.py`): the Stage-B packet is built from
  a hard-coded whitelist `{artifact files, rubric, hash-verified criteria, references}` with a
  provenance assertion; the decision log can never leak in. Each rework round gets a fresh
  reviewer.
- **Icarus seam** (`harness/icarus/builder.py`): `Builder.build(BuildPacket) -> BuildResult`;
  `status` is a claim with zero authority. Fully swappable (local LLM / ensemble / stub).
- **Self-mod validator** (`harness/selfmod/validator.py`): re-proves certification from
  scratch, requires the regression suite green, a changelog entry, and no silent floor drop /
  fixture deletion; records a one-command revert token.

## Repo layout (target — follows docs/PLAN.md)

```
harness/  loop.py gatekeeper.py states.py models.py ratchet.py
          checks/{base,registry,builtin}.py fixtures/
          review/{base,packet_builder}.py   icarus/builder.py
          selfmod/validator.py  metrics/  HARNESS_CHANGELOG.md
game/     # Godot project (GDScript) — Phase 3.5+
control/  # FastAPI+HTMX dashboard + heartbeat + Start/Stop/Pause — Phase 3
docs/     PLAN.md EXECUTION_PLAN.md
tests/    test_walking_skeleton.py
```

## Phasing (walking skeleton first)

- **Phase 0 — Env + git plumbing.** Install Godot; prove headless export + screenshot via
  Xvfb. Stand up changelog + one-command revert. Defer the text-to-3D spike.
- **Phase 0.5 — Walking skeleton. ✅ DONE.** Real Gatekeeper + state machine + `criteria_hash`
  freeze, `StubBuilder`, one certified check, `StubReviewer` (FAIL-then-PASS). Proves the whole
  structural core at zero LLM/art cost.
- **Phase 1 — Real deterministic check runner. ✅ DONE.** Real code checks (Python-syntax,
  JSON) + CV checks (image loadable / min-resolution / not-blank, via Pillow) join the trivial
  `non_empty_artifact` check; explicit `CheckCost` tiers make Stage A cost-tiered (cheap FAIL
  short-circuits expensive pixel analysis); checks emit numeric metrics the Gatekeeper mints as
  monotonic ratchet floors. 31 governance tests green.
- **Phase 2 — Reviewers + four teeth. ✅ DONE.** Real Stage-B reviewer behind a `ChatClient`
  seam (`LLMReviewer`; scripted offline, Anthropic Opus in prod), multi-model `ConsensusReviewer`
  that fails closed on disagreement, decision-log→new-check flywheel, a decomposed
  reference-anchored CV visual gate validated on a committed labeled good/bad image set, plateau
  detection wired into the loop as an independent escalation trigger, and hard-blocking cold
  audits. 51 governance tests green. (Live wiring of the visual gate to real reference art lands
  with One Pond in Phase 4.)
- **Phase 3 — Real Icarus + control surface. ✅ DONE.** `LLMBuilder` (Icarus) behind a swappable
  `GenerationClient` seam; durable `RunStore` (mode + heartbeat + records + autonomy metric);
  `AutonomousRunner` that processes a ticket queue unattended, auto-escalates to the escape-hatch
  builder on plateau (never asks a human), and stops cleanly on Pause/Stop; stdlib read-only
  dashboard with `/heartbeat` + Start/Stop/Pause. 63 governance tests green. (Local-model /
  paid-API generation client is a drop-in behind the seam.)
- **Phase 3.5 — Text-to-3D spike.** Pick a generator (behind the GPU-worker seam) by measured
  quality against Phase-2 labeled fixtures; fallback to curated packs.
- **Phase 4 — Build "One Pond" through the harness.** Fixed iso camera, 3 AI-generated
  low-poly buildings, bread-economy tick, place-a-building + save. Measure and drive up Icarus
  autonomy rate. The true test.

## Verification

1. **Gate is real:** bad artifact → Stage A/B FAIL, no commit; good → PASS, commit, fixture
   minted. (`tests/test_walking_skeleton.py`.)
2. **Builder can't self-approve:** no commit path outside the Gatekeeper; a `COMPLETED` claim
   with a failing artifact still does not commit.
3. **Criteria immutable:** post-freeze edit → `ABORTED_TAMPER`.
4. **Ratchet holds:** reintroduced defect caught automatically; floors only rise absent an
   explicit `baseline_reset`.
5. **Self-mod safe:** a change that reddens the suite / adds an uncertified check / omits the
   changelog / silently lowers a floor is blocked.
6. **Reviewer isolation:** Stage-B packet provenance equals the whitelist; no decision-log
   content.
7. **Visual gate sees (Phase 2):** prompt library scores the labeled image set correctly;
   multi-model disagreement catches a single-model wrong verdict.
8. **Anti-complacency fires (Phase 2):** simulated plateau → escalation; cold audit findings
   hard-block.
9. **Flywheel visible (Phase 4):** dashboard shows autonomy rate rising, interventions falling.

Run the proven part now: `pip install -r requirements.txt && python -m pytest tests/ -q` → `20 passed`.

## Risks / open dependencies

- Godot headless screenshot needs Xvfb (not `--headless`); prove in Phase 0.
- No GPU in the current box for text-to-3D — generator runs on a remote GPU host behind the
  worker seam; fallback to curated packs.
- External visual model for multi-model consensus must be free/autonomous.
- Plateau/cold-audit thresholds must be concrete numeric metrics wired into `metrics/`.
- Expect heavy escape-hatch (Claude) building early — that's the signal that drives Icarus
  upgrades, not a failure.
