# Self-distillation runbook — raising Icarus's UNAIDED capability

The one genuinely-open frontier (see `docs/SCORECARD.md`): unaided pass@1 sits in a ~0.73–0.85 band,
largely model-limited on the 16 GB card. Base-runtime levers (prompt, routing, step-cap) are exhausted.
The plan's real lever (Part 5, Levers 3 & 5) is **self-distillation**: fine-tune the local model on
Icarus's OWN gate-passing solutions, then keep the adapter ONLY if the unaided battery rises.

This is the concrete workflow. Steps 1–2 are built and run here; step 3 is an external GPU job.

## 1. Generate the training data (built — `python ops/build_sft.py`)
`harness/icarus/distill.py` pairs each authored ticket with the module Icarus built that CLEARED the gate
(behavioural check + reviewer) and writes `data/onepond_sft.jsonl` in the standard
`{"instruction","input","output"}` shape. The instruction is the FULL spec (title + acceptance criteria +
`{call == expect}` contracts); the output is the verified solution. Only gate-passing modules are included,
so the data is correct by construction (guarded by `tests/test_distill.py`). Grow it by authoring +
building more tickets — each adds a diverse verified pair (currently ~20 across formula/boolean/string/
search/dict/sort shapes).

## 2. Sanity-check the data
`python -m pytest tests/test_distill.py -q` — every record is valid JSONL and every `output` parses as
Python. Eyeball a few: instructions should read as real tasks, outputs as clean modules.

## 3. QLoRA fine-tune (EXTERNAL GPU job — not run here)
Ollama serves GGUF; QLoRA needs the base HF weights. Practical path:
- Pick a QLoRA-able base that matches the runtime brain family (e.g. the Qwen3-14B base behind the
  Hermes profile, or an HF build of the resident model). Keep it small enough to fine-tune + serve in 16 GB.
- Train a LoRA adapter on `data/onepond_sft.jsonl` with a standard stack (e.g. `unsloth`/`peft` +
  `trl SFTTrainer`), short (1–3 epochs, low LR), penalising reasoning-length bloat (PLAN Lever 4).
- Merge/convert to GGUF and `ollama create icarus-sft -f Modelfile`.

## 4. Measure — the ONLY thing that decides keep/revert
Re-run the sealed unaided battery with the new model:
`OllamaAgentModel("icarus-sft")` through `harness.icarus.eval.run_battery(..., use_notebook=False)` on a
FRESH seed set (never the ones distilled from — anti-memorisation). Compare unaided pass@1 to the
gpt-oss:20b baseline in `docs/SCORECARD.md`. **Keep the adapter ONLY if unaided-on-novel rose and variety
didn't collapse; else revert.** Log the before→after in `docs/ICARUS_CHANGELOG.md` (the plan's Step E).

## 5. Loop
More authored tickets → more verified pairs → periodically re-fine-tune → re-measure. As unaided rises,
the dependence gap (assisted − unaided) SHRINKS: Icarus internalises what the notebook/routing used to
carry. That shrinking gap, not the assisted autonomy rate, is the real success signal.
