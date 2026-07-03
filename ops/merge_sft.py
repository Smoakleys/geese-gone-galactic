"""Merge all self-distillation datasets into one QLoRA-ready training file.

Combines every `data/*_sft.jsonl` (authored + all generated batches) into `data/training_all.jsonl`,
de-duplicating by solution `output` so repeated instances don't over-weight. That merged file is the
input to the external QLoRA fine-tune (see docs/DISTILL.md). Run: `python ops/merge_sft.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def merge(data_dir: Path, out_name: str = "training_all.jsonl") -> "tuple[int, int]":
    """Merge every *_sft.jsonl in `data_dir` into `out_name`, deduped by output. Returns (kept, seen)."""
    data_dir = Path(data_dir)
    seen: "set[str]" = set()
    records: "list[dict]" = []
    total = 0
    for p in sorted(data_dir.glob("*_sft.jsonl")):
        for ln in p.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            total += 1
            key = r.get("output", "")
            if key in seen:
                continue
            seen.add(key)
            records.append({k: r[k] for k in ("instruction", "input", "output") if k in r})
    out = data_dir / out_name
    with out.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records), total


def main() -> None:
    data = Path(__file__).resolve().parents[1] / "data"
    kept, total = merge(data)
    print(f"merged {kept} unique records (from {total} total) -> data/training_all.jsonl")


if __name__ == "__main__":
    main()
