# Harness (structural core)

This is the **structural core** of the GGG v3 harness: the strict gate that no builder can
route around. The governance thesis was proven first with stubs (Phase 0.5) *before* any real
LLM builder, reviewer, or art pipeline existed; the seams below are now filled in and all
phases (0.5–4) plus the taste→gate flywheel are complete in software (see `docs/AUTOPILOT.md`
for live status, `docs/CHECKS.md` for the gate catalog). The core is stdlib-only Python and
runs with zero LLM/GPU cost; the real model/GPU pieces are drop-ins behind the seams.

## The one idea

**Commit authority lives in the `Gatekeeper`, not in any agent.** Builders write only to a
gitignored staging dir and have no commit function. The `Gatekeeper` is the only code path
that promotes staging → the protected tree and runs `git commit`, and it does so only after an
independent reviewer's default-FAIL `Verdict` passes. "The builder can't approve its own work"
is therefore a property of the wiring, not of anyone's discipline.

## Modules

| Module | Role |
|---|---|
| `models.py` | Ticket / Verdict / BuildPacket data model; `criteria_hash` freeze; default-FAIL verdicts |
| `states.py` | State machine; the only edge into `COMMIT_PENDING` is `STAGE_B_PASS` |
| `loop.py` | Drives the iteration; holds **no** commit authority |
| `checks/` | Check contract + fixture-based **certification** + `registry.lock`; cost-tiered Stage A runner. Checks: `code.py` (Python-syntax, JSON — total functions, never crash the loop), `image.py` (loadable / min-resolution / not-blank, via Pillow). Game checks live in `game/onepond/checks.py`. |
| `gatekeeper.py` | Sole commit authority; tamper checks; **ratchet floor gate** (refuses any regression below an established floor); ratchet minting |
| `ratchet.py` | Monotonic quality floors (`floor = max(old, new)`); regression fixtures |
| `review/` | Reviewer contract + isolation **packet builder**; `llm_reviewer.py` / `consensus.py` (multi-model, fail-closed) behind a `ChatClient` seam (`model_client.py`, Anthropic in prod); `visual_gate.py` (reference-anchored CV scorer); `decision_log_review.py` (Stage C flywheel: `new_check` / `tighten_rubric` proposals) |
| `audit/` | Cold audits — periodic, hard-blocking re-verification of accepted work (mechanical + adversarial) |
| `icarus/` | The swappable `Builder` seam. **`agent/`** = Icarus's agent **runtime** (plan→act→reflect loop + tools: edit/read/list/search/run/see(vision)/render/note; resilient to transient model failures). **`agent_builder.py`** = `AgentBuilder` (the runtime behind the Builder seam) + `ModelRouter` (visual/Godot tickets → a 30B, logic → fast gpt-oss:20b). **`eval/`** = the procedural capability battery (scores UNAIDED problem-solving on novel tasks). `LLMBuilder` (one-shot `GenerationClient`) is the legacy generator. |
| `gen3d/` | Text-to-3D `MeshGenerator` seam + curated-pack fallback; real GPU worker is a drop-in |
| `selfmod/` | The guard-railed self-modification validator + revert bookkeeping |
| `metrics/` | Autonomy-rate flywheel metric + plateau detection |

The control surface (`control/`, outside this package) adds a durable `RunStore`, the
`AutonomousRunner`, and a stdlib read-only dashboard — it only reads the store, never the gate.

## Run the governance suite

```bash
pip install -r requirements.txt      # pytest (+ PyYAML for later phases)
python -m pytest tests/ -q
```

The suite proves, in order: the state graph has a single commit predecessor; a broken check is
refused certification; a bad artifact FAILs and does not commit; a builder's `COMPLETED` claim
does not commit if review fails; a good artifact commits exactly once; empty-evidence "PASS" is
FAIL; post-freeze criteria edits abort as tamper; a reintroduced defect is caught by the
ratchet; self-mod is blocked when it reddens the suite / adds an uncertified check / omits the
changelog / silently lowers a floor; and the Stage-B review packet never sees the decision log.

## Live now (built this cycle) + what remains external

Built and exercised locally (see `docs/HANDOFF.md`):
- **Godot 4 + a Windows offscreen screenshot rig** (`tools/godot_capture/`, `game/godot/`) — replaces
  the Linux `GodotXvfbWorker`; `godot_parse` + `green_dominance` render checks gate real GDScript.
- **Icarus's agent runtime + routing** (`harness/icarus/agent/`, `agent_builder.py`) on local Ollama
  (gpt-oss:20b + qwen3:30b). Proven end-to-end: Icarus → full gate → committed, rendered scene.

Still external, each a swap behind a tested seam:
- **GPU text-to-3D** — `RemoteGpuWorker` behind `harness/gen3d`; a curated pack is the fallback.
- **A stronger reviewer** — behind the `ChatClient` seam; the local advisory judge + deterministic gate
  run fully offline today.

Everything above the seams — the loop, the gate, the ratchet, Stage C (works with the agent), cold
audits, the control surface — is real and covered by the governance suite (218 tests).
