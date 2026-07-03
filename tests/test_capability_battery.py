"""Tests for the procedural capability battery + scorer (offline, scripted agent)."""

from __future__ import annotations

from random import Random

import pytest

from game.godot.binary import godot_path
from harness.icarus.agent import ScriptedAgentModel
from harness.icarus.eval import run_battery, sample_battery
from harness.icarus.eval.capability import gen_find_secret, gen_fix_bug, gen_gdscript, gen_sum


def test_sample_battery_reproducible_and_varies():
    a = [t.id for t in sample_battery(seed=0)]
    b = [t.id for t in sample_battery(seed=0)]
    c = [t.id for t in sample_battery(seed=1)]
    assert a == b            # same seed -> same instances
    assert a != c            # different seed -> different instances (non-memorizable)
    from harness.icarus.eval.capability import default_generators
    assert len(a) == len(default_generators())   # one per default generator


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


def test_bakery_scene_verifier_needs_a_building(tmp_path, monkeypatch):
    # verify passes only when the render shows ground + a building (>=3 colour regions), not a bare plane.
    import game.godot.capture as cap
    from PIL import Image
    from harness.icarus.eval.capability import gen_bakery_scene
    inst = gen_bakery_scene(Random(0))
    ws = tmp_path / inst.id
    ws.mkdir()
    (ws / "scene.gd").write_text("extends Node3D\n")

    def good(gd, out, **k):  # bg gray + green ground + brown building = 3 colours
        im = Image.new("RGB", (60, 60), (100, 100, 100))
        for y in range(15, 45):
            for x in range(60):
                im.putpixel((x, y), (0, 200, 0))
        for y in range(25, 40):
            for x in range(22, 40):
                im.putpixel((x, y), (139, 69, 19))
        im.save(out)
        return True, "rendered"

    monkeypatch.setattr(cap, "render_gdscript", good)
    ok, detail = inst.verify(ws)
    assert ok, detail

    def bare(gd, out, **k):  # flat green ground, no building
        Image.new("RGB", (60, 60), (0, 200, 0)).save(out)
        return True, "rendered"

    monkeypatch.setattr(cap, "render_gdscript", bare)
    bad, detail = inst.verify(ws)
    assert not bad and "building" in detail


def test_placement_verifier(tmp_path):
    import re

    from harness.icarus.eval.capability import gen_placement
    inst = gen_placement(Random(0))
    m = re.match(r"place_n(\d+)_(.+)", inst.id)
    n = int(m.group(1))
    cells = [tuple(map(int, p.split("x"))) for p in m.group(2).split("_")]
    seen, valid = set(), True
    for x, y in cells:
        if not (0 <= x < n and 0 <= y < n) or (x, y) in seen:
            valid = False
            break
        seen.add((x, y))
    expected = "VALID" if valid else "INVALID"
    ws = tmp_path / inst.id
    ws.mkdir()
    (ws / "place.py").write_text(f"print('{expected}')\n")
    ok, _ = inst.verify(ws)
    assert ok
    (ws / "place.py").write_text(f"print('{'INVALID' if expected == 'VALID' else 'VALID'}')\n")
    bad, _ = inst.verify(ws)
    assert not bad


def test_economy_verifier(tmp_path):
    import re

    from harness.icarus.eval.capability import gen_economy
    inst = gen_economy(Random(0))
    b, g, t, s = map(int, re.match(r"economy_(\d+)b_(\d+)g_(\d+)t_(\d+)s", inst.id).groups())
    final = s + t * (b * 3 - g)
    ws = tmp_path / inst.id
    ws.mkdir()
    (ws / "economy.py").write_text(f"print({final})\n")
    ok, _ = inst.verify(ws)
    assert ok
    (ws / "economy.py").write_text("print(0)\n")
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


def test_run_battery_with_router_scores(tmp_path):
    from harness.icarus.agent_builder import visual_router
    inst = gen_sum(Random(0))
    a, b = (int(x) for x in inst.id.split("_")[1:])
    solver = ScriptedAgentModel([f'```tool\nname: write_file\npath: solution.py\nbody:\nprint({a + b})\n```',
                                 '```tool\nname: finish\nsummary: done\n```'])
    solver.model_id = "solver"
    other = ScriptedAgentModel([])
    other.model_id = "other"
    # a logic task routes to the default (solver), which solves it
    report = run_battery(None, [inst], tmp_path, router=visual_router(fast=solver, big=other), max_steps=6)
    assert report.pass_rate == 1.0


def test_run_battery_requires_model_or_router(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        run_battery(None, [], tmp_path)


def test_run_battery_scores_wrong_answer_as_fail(tmp_path):
    inst = gen_sum(Random(0))
    replies = [
        '```tool\nname: write_file\npath: solution.py\nbody:\nprint(-1)\n```',
        '```tool\nname: finish\nsummary: done\n```',
    ]
    report = run_battery(ScriptedAgentModel(replies), [inst], tmp_path, max_steps=6)
    assert report.pass_rate == 0.0
    assert not report.results[0].passed


def test_fixbug_setup_seeds_broken_file(tmp_path):
    inst = gen_fix_bug(Random(0))
    a, b = (int(x) for x in inst.id.split("_")[1:])
    ws = tmp_path / inst.id
    ws.mkdir()
    inst.setup(ws)
    assert (ws / "solution.py").exists()
    ok, _ = inst.verify(ws)          # as-seeded it is broken
    assert not ok
    (ws / "solution.py").write_text(f"print({a + b})\n")  # fix it
    ok2, _ = inst.verify(ws)
    assert ok2


def test_green_dominance_distinguishes_green_from_gray_and_black(tmp_path):
    # Regression for TWO gate bugs found by looking at real renders: a green plane that fills the
    # frame (uniform, ~0 variance) IS valid, and a uniform GRAY background (camera saw nothing) is
    # NOT valid even though it's bright. green_dominance passes only a real green scene.
    from PIL import Image
    from game.godot.capture import green_dominance

    def mk(name, rgb):
        p = tmp_path / name
        Image.new("RGB", (32, 32), rgb).save(p)
        return p

    assert green_dominance(mk("green.png", (0, 255, 0))) >= 15   # a green scene rendered
    assert green_dominance(mk("gray.png", (77, 77, 77))) < 15    # gray background == empty (the miss)
    assert green_dominance(mk("black.png", (0, 0, 0))) < 15      # black == blank


def test_significant_colors_counts_regions(tmp_path):
    # the deterministic "ground + a building" gate for the next breadth item (bakery scene)
    from PIL import Image
    from game.godot.capture import significant_colors

    flat = tmp_path / "flat.png"
    Image.new("RGB", (64, 64), (0, 255, 0)).save(flat)
    assert significant_colors(flat) == 1                        # ground only

    two = Image.new("RGB", (64, 64), (0, 255, 0))              # ground + background
    for y in range(32):
        for x in range(64):
            two.putpixel((x, y), (100, 100, 100))
    p2 = tmp_path / "two.png"
    two.save(p2)
    assert significant_colors(p2) == 2

    three = Image.new("RGB", (60, 60), (100, 100, 100))        # bg + ground + a building
    for y in range(20):
        for x in range(60):
            three.putpixel((x, y), (0, 255, 0))
    for y in range(20, 40):
        for x in range(60):
            three.putpixel((x, y), (139, 69, 19))
    p3 = tmp_path / "three.png"
    three.save(p3)
    assert significant_colors(p3) >= 3

    # a SMALL building (~3% of frame, like a real iso bakery box) must still count as a 3rd region --
    # regression for a too-strict 0.04 threshold that failed a real render (looked at the pixels).
    small = Image.new("RGB", (100, 100), (100, 100, 100))      # bg
    for y in range(40, 100):
        for x in range(100):
            small.putpixel((x, y), (0, 255, 0))                # ground (60%)
    for y in range(55, 73):
        for x in range(41, 59):
            small.putpixel((x, y), (139, 69, 19))              # building 18x18 = 3.24%
    ps = tmp_path / "small.png"
    small.save(ps)
    assert significant_colors(ps) == 3


@pytest.mark.skipif(godot_path() is None, reason="Godot not installed")
def test_gdscript_verifier(tmp_path):
    inst = gen_gdscript(Random(0))
    ws = tmp_path / inst.id
    ws.mkdir()
    missing, _ = inst.verify(ws)          # no scene.gd yet
    assert not missing
    (ws / "scene.gd").write_text("extends Node3D\nfunc _ready() -> void:\n\tadd_child(Camera3D.new())\n")
    ok, detail = inst.verify(ws)          # valid GDScript
    assert ok, detail
    (ws / "scene.gd").write_text("extends Node3D\nfunc _ready() -> void\n\tpass\n")  # missing colon
    broke, _ = inst.verify(ws)
    assert not broke


def test_find_secret_setup_and_verify(tmp_path):
    inst = gen_find_secret(Random(0))
    token = inst.id.split("_")[1]
    ws = tmp_path / inst.id
    ws.mkdir()
    inst.setup(ws)
    assert f"SECRET={token}" in (ws / "data.txt").read_text()
    (ws / "answer.txt").write_text(token + "\n")
    ok, _ = inst.verify(ws)
    assert ok
    (ws / "answer.txt").write_text("WRONG\n")
    bad, _ = inst.verify(ws)
    assert not bad
