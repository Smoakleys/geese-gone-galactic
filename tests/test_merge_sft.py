"""Merge of the self-distillation datasets into one QLoRA-ready file."""

from __future__ import annotations

import json

from ops.merge_sft import merge


def test_merges_and_dedups(tmp_path):
    (tmp_path / "a_sft.jsonl").write_text(
        '{"instruction":"aaaaaaaaaaaaaaaaaaaaaa","input":"","output":"print(1)"}\n'
        '{"instruction":"bbbbbbbbbbbbbbbbbbbbbb","input":"","output":"print(2)"}\n', encoding="utf-8")
    (tmp_path / "b_sft.jsonl").write_text(
        '{"instruction":"cccccccccccccccccccccc","input":"","output":"print(2)"}\n'   # dup output
        '{"instruction":"dddddddddddddddddddddd","input":"","output":"print(3)"}\n', encoding="utf-8")
    kept, total = merge(tmp_path)
    assert total == 4 and kept == 3                       # one dup removed
    lines = (tmp_path / "training_all.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    for ln in lines:
        assert {"instruction", "input", "output"} == set(json.loads(ln))


def test_merge_runs_as_a_script():
    # verify end-to-end: `python ops/merge_sft.py` runs and writes the merged training file.
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(repo / "ops" / "merge_sft.py")],
                       capture_output=True, text=True, cwd=str(repo), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "unique records" in r.stdout
    assert (repo / "data" / "training_all.jsonl").exists()
