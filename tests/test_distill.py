"""Self-distillation SFT data pipeline (harness-mod-51)."""

from __future__ import annotations

import json
from pathlib import Path

from harness.icarus.distill import build_sft_records, write_jsonl
from game.onepond_tickets import one_pond_tickets


POND = Path(__file__).resolve().parents[1] / "game" / "pond"


def test_builds_one_record_per_committed_module():
    records = build_sft_records(one_pond_tickets(), POND)
    # every logic ticket whose module is committed contributes exactly one instruction->solution pair
    assert len(records) >= 10
    for r in records:
        assert r["instruction"] and r["output"]                 # real task + real solution
        assert "def " in r["output"]                            # the committed module source
        assert (POND / r["meta"]["module"]).exists()            # only verified successes


def test_writes_qlora_jsonl(tmp_path):
    records = build_sft_records(one_pond_tickets(), POND)
    out = tmp_path / "sft.jsonl"
    n = write_jsonl(records, out)
    assert n == len(records)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == n
    first = json.loads(lines[0])
    assert {"instruction", "input", "output"} <= set(first)     # standard QLoRA shape


def test_skips_uncommitted_modules(tmp_path):
    # a ticket whose module isn't in the dir yields no record (only verified successes are distilled)
    records = build_sft_records(one_pond_tickets(), tmp_path)    # empty dir
    assert records == []
