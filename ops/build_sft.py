"""Regenerate the self-distillation SFT dataset from Icarus's gate-passing One Pond modules.

Run: `python ops/build_sft.py`  ->  writes data/onepond_sft.jsonl (QLoRA-ready {instruction,input,output}).

Each record is a ticket description paired with the module Icarus built that CLEARED the strict gate
(behavioural check + reviewer), so the data is verified by construction. The next step is external: QLoRA
fine-tune the local model on this data to raise *unaided* capability past the base-model ceiling (PLAN
Part 5, Levers 3 & 5). This script only prepares the data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.icarus.distill import build_sft_records, write_jsonl  # noqa: E402
from game.onepond_tickets import one_pond_tickets                  # noqa: E402


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    records = build_sft_records(one_pond_tickets(), repo / "game" / "pond")
    out = repo / "data" / "onepond_sft.jsonl"
    n = write_jsonl(records, out)
    print(f"wrote {n} gate-passing SFT records to {out.relative_to(repo).as_posix()}")
    return n


if __name__ == "__main__":
    main()
