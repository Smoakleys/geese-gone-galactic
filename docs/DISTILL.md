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
building more tickets — each adds a diverse verified pair (currently ~22 across 8 shapes: formula/boolean/
string/search/dict/sort/iteration/set).

**SCALING to the hundreds/thousands QLoRA wants (PLAN Lever 1 — the procedural battery).** Hand-authored
tickets don't scale; the `gen_*` generators in `harness/icarus/eval/capability.py` produce INFINITE
non-repeating instances, each with its own deterministic checker. The batch data-gen job (a long GPU run,
same class as the QLoRA step): loop over seeded generator instances → run each through the agent loop
(`OllamaAgentModel` + the runtime) → keep ONLY instances whose checker passes → append `{instruction:
prompt, output: the solution Icarus wrote}` to the dataset. Best-of-N per instance (keep the passing
sample) raises yield. This is Atropos's `--save-top-n-per-group` pattern: infinite gym + gate filter =
large, verified, non-memorisable SFT data with no hand-authoring.

## 2. Sanity-check the data
`python -m pytest tests/test_distill.py -q` — every record is valid JSONL and every `output` parses as
Python. Eyeball a few: instructions should read as real tasks, outputs as clean modules.

## 3. QLoRA fine-tune (EXTERNAL GPU job — not run here)

**Local feasibility CHECKED 2026-07-03 — confirmed external.** None of the training stack is installed on
this box (`torch`, `transformers`, `peft`, `trl`, `bitsandbytes`, `unsloth`, `datasets`, `accelerate` all
missing). Beyond install, the blocker is hardware: the AMD RX 9070 XT is **RDNA4**, whose ROCm *training*
support is bleeding-edge, and 4-bit QLoRA needs `bitsandbytes`, whose ROCm/RDNA4 support is minimal. Ollama
*inference* works on this card; *training* is a different, uncertain path. So the fine-tune is not a
per-cycle increment — it needs a deliberate setup (most reliably a **cloud/CUDA GPU** for a few hours), the
data (ready: ~125 clean pairs, grown via six procedural batches), and the measure-keep-or-revert gate below. The data pipeline is done and waiting;
the compute is the gap.

The training SCRIPT is already written + TURNKEY: **`ops/train_qlora.py`** (its data-loading half is
unit-tested in `tests/test_train_qlora.py`; the GPU `train()` is the external part). On a cloud/CUDA box:
```
pip install torch transformers peft trl datasets bitsandbytes accelerate
python ops/merge_sft.py                                          # assemble data/training_all.jsonl
python ops/train_qlora.py --base <hf-model> --data data/training_all.jsonl --out out/icarus-sft
```
It applies a standard QLoRA recipe (4-bit + peft LoRA on all attn+MLP projections + trl SFTTrainer, 2
epochs, low LR) with a train==serve prompt template. Notes: pick a QLoRA-able base matching the runtime
brain family (small enough to fine-tune + serve in 16 GB); then merge/convert the adapter to GGUF and
`ollama create icarus-sft -f Modelfile`. **The corpus grows via CLEAN procedural batches** (23
non-hardcodable generators now; `ops/generate_training_data.py` — run with NO concurrent load, the
contamination lesson).

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
