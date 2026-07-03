# Speed investigation — Icarus build latency (2026-07-03)

Prompted by an OP-1 scene build taking ~20 min. Goal: make Icarus's builds fast enough to iterate.

## Measured facts (clean, GPU uncontended)
| Model | Fits 16GB? | Speed | Renders scenes? |
|---|---|---|---|
| **gpt-oss:20b** (11.9GB) | YES — fully resident | ~86 tok/s gen, fast prompt | simple plane 2/3; **real pond scene 0/2** |
| **qwen3:30b** (20.1GB) | **NO** — ~78% resident, 22% on CPU | ~43 tok/s gen (offloaded) | pond scene 3/3 (but slow) |

- **The 30B cannot fit.** At `num_ctx` 8192→4096→2048 residency only moves 78%→80% — the *model itself*
  is ~19GB, so shrinking the KV cache doesn't help. It is permanently offloaded → permanently slow.
- **qwen3 reasons verbosely**: ~1,637 generated tokens (mostly `<think>`) for a 5-line request ≈ 38s of
  generation alone, every turn. `think:false` does NOT fix it — the model just reasons inline in `content`.
- **The 20-min build** = many steps × (slow offloaded generation + verbose thinking + reprocessing a
  growing context), sometimes × 2 rework rounds.

## Shipped this pass (pure wins, no quality trade)
- **Context trimming** (harness-mod-36): the model's input is bounded to setup + recent turns instead of
  an ever-growing history — per-turn prompt cost stops climbing with step count.
- **keep_alive="30m"**: the model stays resident instead of reloading between turns.
- **Step-cap 16→10** in `default_icarus_builder`: successful builds finish in ~4-6 steps; the lower cap
  only bites a struggling build, bounding the worst case.

## The real lever (recommendation)
The 30B is a hardware ceiling, so the durable fix is to **stop needing it for visuals**. The fast,
resident gpt-oss:20b already renders *simple* scenes; it fails *complex* ones on scene construction
(camera framing + multiple objects). Two ways to close that gap, in preference order:

1. **Scene template (recommended).** Provide a known-good skeleton — a current orthographic camera framed
   on the origin + the unshaded-material pattern — and make the visual ticket "add your meshes to this
   template." Icarus fills the *content* (which buildings, colours, positions) it's good at; the *framing*
   it fails is given. This lets the FAST resident model build real scenes → ~3-5× faster, more reliable.
   It's a curated scaffold (the plan allows this), removable, and measured against the render gate.
2. **Bake-off for a fitting render-capable model.** Look for a ≤~14GB model that both fits fully AND
   renders (qwen2.5-coder:14b already tried: 0/3). Uncertain; a template is more reliable.

Meanwhile visuals are RARE (scenes are static, built once and committed) — logic tickets (the common
case) already run fast on the resident gpt-oss:20b.

## Template result (measured 2026-07-03) — partial
Built `game/godot/scene_template.py` (`compose_scene` wraps Icarus's `build(root)` with a correct iso
camera) + `gen_pond_from_template`. The mechanism works (a good `build()` composes → renders → passes the
gate). But the FAST model on the templated task scored only **1/3, ~60s/scene**: the camera is now always
right, yet gpt-oss:20b still makes CONTENT errors — e.g. `rotate_x(-90°)` on a `PlaneMesh` (which is
already flat) stands the ground vertical → invisible; wrong colours. Added the plane-rotation gotcha to
the notebook (helps both models). So the template lifts the fast model (0/2 → 1/3) but does not make it
reliable; the honest conclusion stands:

**The 30B remains the reliable scene builder (3/3); it is now faster via the shipped changes (bounded
context + keep_alive + step-cap). Scenes are rare/static, so a ~3-5 min reliable 30B build is acceptable;
the template + fast model is an option for quick iteration when 1/3-and-retry is fine.** A better content
scaffold (helper fns Icarus parameterises) or a fitting render-capable model would close the rest — both
larger, deferred.
