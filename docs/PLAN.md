# Plan: A Strict, Self-Improving Harness for a Locally-Based Game-Dev AI (GGG v3)

## Context

Prior GGG iterations (v1 autonomous studio, v2 rework) kept failing the same way: the
builder self-approved weak work, the visual gate was blind, quality silently regressed,
and **both Icarus and Claude got complacent** — substituting hope for honest checks and
drifting off the operating discipline. The root cause was never a lack of effort; it was
that **nothing structural made bad work or coasting impossible.**

This is a **fresh restart** (old repo stays archived). The goal is a *very strict,
programmatic harness* whose real deliverable is a **locally-based game-dev AI (Icarus)** —
bootstrapped until it can build a genuinely great game. The end-all goal is to **use that
harnessed AI to build a great Geese Gone Galactic (GGG).** The harness must get good fast
enough that we build the game *with* it, not around it.

Non-negotiables baked into the structure (not left to willpower): the builder cannot
approve its own work; quality can only ratchet up; complacency is auto-detected and
punished with escalation; visual judgment is decomposed, reference-anchored, and
cross-checked; and Claude is bound by the same gates it enforces.

> Status: this is a **design/architecture plan only** — no implementation yet.

---

## Core operating model

| Role | Who | Responsibility |
|------|-----|----------------|
| **Builder** | **Icarus** (local model, fully malleable) | Produces ALL game artifacts by default (code + assets). |
| **Architect / Reviewer / Taste authority** | **Claude (Opus)** | Writes tickets + acceptance criteria, reviews, self-modifies the harness, researches. Does **not** build game content — except the narrow escape hatch below. |
| **Clean gate** | **Fresh zero-context Opus** per review | Independent adversarial verdict on each artifact + Icarus's decision log. |

**Build discipline (hard rule, harness-enforced):**
- Every game artifact flows through Icarus. Claude never routinely builds game content.
- **Escape hatch:** Claude may build *only when Icarus genuinely cannot get it.* When it
  does, (a) Claude's output goes through the **same** clean-review gate, and (b) the real
  deliverable of that episode is that Claude then **upgrades Icarus** so next time Icarus
  can. A Claude-build is a *diagnostic*, not a shortcut.
- **Icarus is totally malleable.** Claude has total control over the Icarus subsystem —
  prompt, packet format, tooling, scaffolding, decomposition, **and the model itself**
  (swap size/model, ensemble, fine-tune — anything). Nothing about Icarus is treated as
  fixed.

**Local vs cloud:** the *builder* is local (that's the "locally-based AI" we bootstrap);
cloud Opus is only reviewer + architect + researcher. Long-term Claude's share shrinks
toward zero.

---

## The iteration = one ticket

1. **Ticket authored** by Claude: a bounded unit of game work with **explicit, testable
   acceptance criteria written BEFORE Icarus starts** (kills goalpost-moving).
2. **Icarus builds** the ticket, logging its decisions + reasoning to a structured
   decision log.
3. **Layered gate:**
   - **Stage A — deterministic checks (cheap, every iteration):** compile/export, tests,
     lint, asset-import success, scale/scene sanity, plus growing CV/asset checks. Fail
     fast here before spending an Opus review.
   - **Stage B — clean adversarial Opus review (on pass of A):** fresh zero-context Opus
     judges the artifact against the **pre-committed criteria + rubric + references**.
     Default verdict is **FAIL**; work must be argued *up* with evidence. "Looks fine" is
     an auto-reject.
   - **Stage C — decision-log review (sampled/batched, not every micro-choice):** Opus
     reviews *how Icarus reasoned* and emits proposed **harness adjustments**.
4. **Verdict is hard-enforced by harness code.** FAIL ⇒ not accepted, no commit; loops
   back to Icarus with the specific defects until it earns a PASS. The builder physically
   cannot mark its own work done.
5. **On PASS:** commit, and the artifact becomes a **regression fixture** (see ratchet).

---

## Anti-complacency structure (the four teeth — for Icarus AND Claude)

1. **Adversarial default-FAIL reviewer.** Fresh, zero-context, assumes not-good-until-
   proven; sees only artifact + rubric + criteria + references, never the builder's
   justifications.
2. **Monotonic quality ratchet.** Every accepted artifact becomes a regression fixture in
   the check-suite; quality can never silently drop, and the bar only rises.
3. **Plateau detection ⇒ auto-escalation.** If autonomy rate or quality stalls for N
   iterations, the harness automatically escalates — bigger swings, deeper research,
   harder critique — instead of coasting.
4. **Periodic cold audits.** A fresh Opus is tasked to red-team the whole project ("prove
   this is mediocre"); findings hard-block. **Claude is bound by the same gates it
   enforces** — it cannot exempt itself.

---

## Guard-railed harness self-modification (the bootstrap engine)

Opus edits the harness **autonomously and often** (Icarus doesn't wait on the owner), but
every change is bounded:
- Git-versioned; logged in `HARNESS_CHANGELOG.md` with rationale; **one-command revert.**
- Must keep the **full check-suite + Icarus's own tests green.**
- **New deterministic checks must pass on known-good AND known-bad fixtures** before they
  count (no check ships unless it provably catches the defect it targets and doesn't flag
  good work).

Every subjective defect the clean reviewer catches is, where possible, folded into a new
deterministic check — turning taste into objective gates over time.

---

## Visual understanding pillar (your #1 historical failure)

The visual gate must genuinely *see*, not vibe:
- **Decomposed:** judgment is a set of concrete sub-questions (scale hierarchy, silhouette
  variety, style/color consistency across assets, composition, clean geometry, "would a
  shipped game use this") — never one vague "is it good."
- **Reference-anchored:** every judgment is an explicit A/B against concept sheets + real
  shipped-game references, not judged in a vacuum.
- **Multi-model:** Opus vision + a strong external model must agree; disagreement forces
  escalation.
- **Deterministic CV where possible:** bounding boxes, color histograms, edge/symmetry,
  poly-count sanity.
- **Tested prompt library:** the visual-review prompts are themselves versioned and tested
  against a **labeled known-good/known-bad image set** — wrong verdicts on that set are
  bugs to fix. Prompting quality is a research task, not an afterthought.

---

## Research pillar

Research is a **first-class, always-available loop action** — Claude researches whenever
it could help (better prompting, text-to-3D techniques, visual-eval methods, Godot
patterns, model choices for Icarus). Findings are logged to `RESEARCH_LOG.md` and, when
actionable, become harness changes or new checks. Standing research fronts: **(a) true
visual understanding/eval methodology, (b) correct prompting** for both asset generation
and reviews.

---

## Art pipeline as a first-class subsystem (flagged high-risk)

Art is **AI-generated low-poly 3D** — your chosen path and your biggest risk (text-to-3D
is inconsistent on style/scale/geometry). So the pipeline gets its own gates:
`generate → import to Godot → iso-screenshot → gate (style/scale consistency, poly sanity,
clean geometry, concept match)`. Prefer **open/local** text-or-image-to-3D
(Hunyuan3D / TRELLIS-class) per the free+autonomous rule; paid APIs only if a local route
can't hit the bar. A short **spike** picks the generator by measured output quality.

---

## Metrics (the flywheel must be visible)

- **North-star: Icarus autonomy rate** — share of gate-passing work Icarus produced with
  **zero** Claude building; target → 100%, "Claude had to intervene" events → 0.
- Secondary (auto-logged): Icarus first-pass PASS-rate, iterations-since-Claude-build, avg
  review rounds per accepted artifact, plateau flag, regression-fixture count.

---

## Owner surface (fully autonomous, lean)

No approval gates in the loop; the system never waits on you. You get: a **live dashboard**
(autonomy rate, plateau flag, current ticket, latest gated screenshot, harness changelog),
a **phone heartbeat**, and a cooperative **Start/Stop/Pause** that pauses both Claude and
Icarus. Runs continuously across plan-budget refreshes with compaction + lean status docs.
Self-authorizing throughout (`never-ask-permissions`).

---

## Concrete first target — vertical slice "One Pond"

The thinnest slice that forces the *entire* harness to work end-to-end:
- Fixed 2.5D iso camera; a single base/pond.
- **3 AI-generated low-poly buildings** (Nest, Bakery, Pond) — exercises the art pipeline
  + visual gate.
- **Bread-economy tick** (resource accrues over time) — exercises systems tickets + tests.
- **Place-a-building** interaction + save — exercises interaction/state tickets.
Conquest / colonies / pond→region→planet→galaxy pullback are explicitly later.

---

## Proposed repo layout (fresh)

```
ggg-v3/
  game/                 # Godot project (GGG)
  harness/
    loop.py             # the strict iteration loop + hard gate enforcement
    tickets/            # ticket specs + pre-committed acceptance criteria
    checks/             # deterministic checks (code+CV), each with good/bad fixtures
    review/             # clean-Opus review, adversarial prompts, decision-log review
    visual/             # decomposed rubric, reference set, labeled fixtures, prompt lib
    icarus/             # builder runner, packet format, model config (fully swappable)
    metrics/            # autonomy rate, plateau detector, logs
    research/           # RESEARCH_LOG.md + tooling
    HARNESS_CHANGELOG.md
  control/              # Start/Stop/Pause GUI + dashboard + phone heartbeat
  docs/                 # EXECUTION_PLAN, DESIGN_BIBLE, references, STATUS
```

---

## Phasing

- **Phase 0 — Env + spikes:** install Godot; confirm headless export + screenshot; spike
  text-to-3D generators and pick one; stand up the labeled visual-fixture set + reference
  images.
- **Phase 1 — Harness skeleton:** loop + hard gate enforcement, ticket/criteria format,
  deterministic check runner with good/bad fixture requirement, git + changelog + revert,
  metrics logging. Prove the gate hard-blocks a deliberately-bad artifact.
- **Phase 2 — Reviewers:** clean adversarial Opus review, decision-log review → harness
  adjustments, visual gate (decomposed + reference-anchored + multi-model + CV + tested
  prompt library), the four anti-complacency teeth.
- **Phase 3 — Icarus + control surface:** builder runner + packet format + swappable
  model; dashboard + phone heartbeat + Start/Stop/Pause.
- **Phase 4 — Build "One Pond" THROUGH the harness:** real tickets, measure autonomy rate,
  drive it up via guard-railed harness/Icarus improvements. This is the true test.

---

## Verification (how we know it works)

1. **Gate is real:** feed a deliberately bad artifact (blob building, broken scale) → it
   must FAIL and refuse to commit. Feed a known-good one → PASS. Both from fixtures.
2. **Ratchet holds:** re-introduce a previously-fixed defect → a regression fixture catches
   it automatically.
3. **Self-mod is safe:** a harness change that breaks the suite is blocked; a new check
   that flags good work (fails its good-fixture) is rejected; revert works in one command.
4. **Visual gate sees:** the prompt library scores the labeled good/bad image set
   correctly; a single-model wrong verdict is caught by multi-model disagreement.
5. **Anti-complacency fires:** simulate a plateau → auto-escalation triggers; run a cold
   audit → its findings hard-block.
6. **Flywheel visible:** dashboard shows autonomy rate rising and interventions falling as
   "One Pond" gets built through the harness.

---

## Flagged risks / dependencies

- **AI-generated 3D consistency** — highest risk; mitigated by the art subsystem + spike,
  but may force a fallback (curated packs) if no generator clears the bar.
- **Godot not yet installed**; headless-screenshot path needs confirming.
- **External visual model route** must be free/autonomous (no owner babysitting).
- **Local-model capability** for 3D scene wiring — expect heavier Claude-build early;
  that's the signal that drives Icarus upgrades, not a failure.
