"""Tests for the procedural capability battery + scorer (offline, scripted agent)."""

from __future__ import annotations

from random import Random

from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.eval import run_battery, sample_battery
from harness.icarus.eval.capability import gen_sum


def test_sample_battery_reproducible_and_varies():
    a = [t.id for t in sample_battery(seed=0)]
    b = [t.id for t in sample_battery(seed=0)]
    c = [t.id for t in sample_battery(seed=1)]
    assert a == b            # same seed -> same instances
    assert a != c            # different seed -> different instances (non-memorizable)
    assert len(a) == 4       # one per default generator


def test_sum_verifier_pass_and_fail(tmp_path):
    inst = gen_sum(Random(0))
    a, b = (int(x) for x in inst.id.split("_")[1:])
    ws = tmp_path / inst.id
    ws.mkdir()
    (ws / "solution.py").write_text(f"print({a + b})\n")
    ok, _ = inst.verify(ws)
    assert ok
    (ws / "solution.py").write_text("print(0)\n")
    bad, _ = inst.verify(ws)
    assert not bad


def test_missing_solution_is_fail(tmp_path):
    inst = gen_sum(Random(3))
    (tmp_path / inst.id).mkdir()
    ok, detail = inst.verify(tmp_path / inst.id)
    assert not ok


def test_run_battery_scores_scripted_solve(tmp_path):
    inst = gen_sum(Random(0))
    a, b = (int(x) for x in inst.id.split("_")[1:])
    replies = [
        f'```tool\nname: write_file\npath: solution.py\nbody:\nprint({a + b})\n```',
        '```tool\nname: run\ncmd: python solution.py\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    report = run_battery(ScriptedAgentModel(replies), [inst], tmp_path, max_steps=6)
    assert report.pass_rate == 1.0, report.summary()
    assert report.results[0].passed and report.results[0].finished


def test_run_battery_scores_wrong_answer_as_fail(tmp_path):
    inst = gen_sum(Random(0))
    replies = [
        '```tool\nname: write_file\npath: solution.py\nbody:\nprint(-1)\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    report = run_battery(ScriptedAgentModel(replies), [inst], tmp_path, max_steps=6)
    assert report.pass_rate == 0.0
    assert not report.results[0].passed
