"""The QLoRA training script's OFFLINE half (data loading/formatting). The GPU train() is external."""

from __future__ import annotations

from pathlib import Path

import pytest

from ops.train_qlora import PROMPT_TEMPLATE, build_texts, format_example, load_records

CORPUS = Path(__file__).resolve().parents[1] / "data" / "training_all.jsonl"


def test_format_example_uses_the_prompt_template_and_the_code():
    text = format_example({"instruction": "do X", "input": "", "output": "print(1)"})
    assert text.startswith(PROMPT_TEMPLATE.format(instruction="do X"))
    assert "print(1)" in text                                  # the target code is the supervised target


def test_load_records_rejects_malformed(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"instruction": "x", "input": "", "output": "   "}\n')   # empty output
    with pytest.raises(ValueError):
        load_records(bad)


@pytest.mark.skipif(not CORPUS.exists(), reason="training_all.jsonl not assembled (run ops/merge_sft.py)")
def test_build_texts_formats_the_real_cleaned_corpus():
    texts = build_texts(CORPUS)
    assert texts, "no training texts produced"
    assert all("### Task:" in t and "### Response:" in t for t in texts)     # train==serve formatting
    assert all(t.strip() for t in texts)
