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


def test_regenerator_runs_as_a_script():
    # ops/build_sft.py must actually run (verify end-to-end, not just import)
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(repo / "ops" / "build_sft.py")],
                       capture_output=True, text=True, cwd=str(repo), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "SFT records" in r.stdout
    assert (repo / "data" / "onepond_sft.jsonl").exists()


def test_committed_sft_datasets_are_wellformed():
    # bad training data poisons the QLoRA fine-tune -- guard EVERY committed *_sft.jsonl (authored +
    # any procedurally-generated dataset).
    import ast
    from pathlib import Path
    data = Path(__file__).resolve().parents[1] / "data"
    files = sorted(data.glob("*_sft.jsonl"))
    assert files, "no SFT datasets committed"
    total = 0
    for p in files:
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for ln in lines:
            r = json.loads(ln)                                 # valid JSONL
            assert {"instruction", "input", "output"} <= set(r), p.name   # standard QLoRA shape
            assert len(r["instruction"]) > 20 and r["output"].strip(), p.name
            ast.parse(r["output"])                             # every solution is valid Python
        total += len(lines)
    assert total >= 15                                          # a real corpus


def test_generate_training_data_plumbing(tmp_path):
    # offline: the solution-picker reads the agent's produced file (the live agent path is smoke-tested
    # separately -- it kept 2/2 gate-passing gen_sum solutions).
    from ops.generate_training_data import _solution_source
    (tmp_path / "solution.py").write_text("print(42)\n")
    assert _solution_source(tmp_path) == "print(42)\n"
    assert _solution_source(tmp_path / "does_not_exist") is None


def test_generate_zero_instances_is_graceful(tmp_path):
    # n=0 must not crash or need a model: empty loop -> empty dataset.
    from ops.generate_training_data import generate
    out = tmp_path / "empty_sft.jsonl"
    n = generate(None, 0, 0, out)
    assert n == 0
    assert out.read_text(encoding="utf-8") == ""
