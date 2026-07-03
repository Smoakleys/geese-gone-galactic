"""QLoRA fine-tune of the runtime brain on Icarus's OWN gate-passing solutions (the plan's Lever 5).

This is the EXTERNAL GPU step of the self-distillation pipeline (docs/DISTILL.md). It is written to be
TURNKEY on a cloud/CUDA box: the data is already assembled + cleaned, so a session with a GPU runs one
command. **NOT runnable on this workstation** — the training stack (torch/transformers/peft/trl/
bitsandbytes) is not installed and the AMD RDNA4 card's training path is unreliable (see docs/DISTILL.md).
The data-loading half IS exercised by tests (test_train_qlora.py) so this file can't silently rot.

Pipeline: `ops/build_sft.py` + `ops/generate_training_data.py` -> `data/*_sft.jsonl` -> `ops/merge_sft.py`
-> `data/training_all.jsonl` (deduped, provenance + hardcoded-literal answers stripped). THEN this script.

Run (on a GPU box, after `pip install torch transformers peft trl datasets bitsandbytes accelerate`):
    python ops/merge_sft.py                       # (re)assemble data/training_all.jsonl
    python ops/train_qlora.py --base <hf-model> --data data/training_all.jsonl --out out/icarus-sft
Then convert the merged adapter to GGUF and `ollama create icarus-sft -f Modelfile`, re-run the CLEAN
unaided battery (ops, no concurrent load), and KEEP the adapter only if unaided pass@1 rises (Step D).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# The prompt template the model is trained (and must later be served) with. Instruction-only, no chat
# frills, matching how Icarus is prompted. Kept module-level so tests assert train == serve formatting.
PROMPT_TEMPLATE = (
    "### Task:\n{instruction}\n\n### Response:\n"
)


def load_records(data_path: "str | Path") -> "list[dict]":
    """Read the merged SFT JSONL. Each line is {instruction, input, output}. Pure/offline + tested."""
    lines = [ln for ln in Path(data_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    records = [json.loads(ln) for ln in lines]
    for r in records:
        if not (r.get("instruction", "").strip() and r.get("output", "").strip()):
            raise ValueError(f"malformed SFT record (empty instruction/output): {r.get('meta')}")
    return records


def format_example(record: dict) -> str:
    """Render one training example: the prompt template + the target code, as a single supervised string."""
    return PROMPT_TEMPLATE.format(instruction=record["instruction"].strip()) + record["output"].rstrip() + "\n"


def build_texts(data_path: "str | Path") -> "list[str]":
    """The full list of supervised strings the trainer consumes. Testable without a GPU."""
    return [format_example(r) for r in load_records(data_path)]


def main() -> None:  # pragma: no cover - the GPU training path is external, not unit-tested
    ap = argparse.ArgumentParser(description="QLoRA fine-tune on Icarus's gate-passing solutions")
    ap.add_argument("--base", required=True, help="HF base model id/path (QLoRA-able, fits + serves in 16GB)")
    ap.add_argument("--data", default="data/training_all.jsonl", help="merged SFT JSONL (ops/merge_sft.py)")
    ap.add_argument("--out", default="out/icarus-sft", help="output dir for the LoRA adapter")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    args = ap.parse_args()

    texts = build_texts(args.data)
    print(f"[train_qlora] {len(texts)} supervised examples from {args.data}")

    # Imported HERE (not at module top) so the file loads + its data helpers test WITHOUT the heavy stack.
    import torch  # noqa: F401
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig)
    from trl import SFTConfig, SFTTrainer

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(args.base)
    tok.pad_token = tok.pad_token or tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base, quantization_config=bnb, device_map="auto")
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)

    ds = Dataset.from_dict({"text": texts})
    cfg = SFTConfig(output_dir=args.out, num_train_epochs=args.epochs, learning_rate=args.lr,
                    per_device_train_batch_size=1, gradient_accumulation_steps=8,
                    max_seq_length=args.max_seq_len, logging_steps=5, save_strategy="epoch",
                    warmup_ratio=0.03, lr_scheduler_type="cosine", bf16=True, dataset_text_field="text")
    SFTTrainer(model=model, train_dataset=ds, args=cfg).train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"[train_qlora] adapter saved to {args.out}. Next: convert to GGUF + `ollama create`, then "
          "re-run the CLEAN unaided battery and keep only if it rises.")


if __name__ == "__main__":
    main()
