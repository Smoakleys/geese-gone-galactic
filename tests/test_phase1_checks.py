"""Phase 1 governance tests — the real deterministic check runner.

Proves the Phase-1 deliverables on top of the walking skeleton:
  * real code checks (Python syntax, JSON validity) certify and catch their defect;
  * real CV checks (loadable, min-resolution, not-blank) certify against image fixtures;
  * Stage A is cost-tiered: cheap STATIC checks run and can reject before any expensive
    DYNAMIC pixel analysis runs (fail-fast);
  * checks emit real numeric metrics that the Gatekeeper mints as monotonic ratchet floors;
  * checks SKIP when they do not apply, so a text ticket is not failed by an image check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.checks.base import CheckCost, cost_of
from harness.checks.builtin import default_registry
from harness.checks.code import JsonValidCheck, PythonSyntaxCheck
from harness.checks.registry import certify
from harness.models import BuildResult, BuildStatus, Result
from harness.review.base import StubReviewer

from conftest import make_ticket

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


# --- helpers --------------------------------------------------------------------------


def _make_loop(git_repo, registry, gatekeeper, tmp_path, *, builder, reviewer, max_rounds=3):
    from harness.loop import Loop
    return Loop(
        repo_root=git_repo, builder=builder, reviewer=reviewer,
        registry=registry, gatekeeper=gatekeeper,
        staging_root=tmp_path / "staging", max_rounds=max_rounds,
    )


def _draw(path: Path, size=(128, 128), blank=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, (120, 120, 120))
    if not blank:
        px = im.load()
        for y in range(size[1]):
            for x in range(size[0]):
                px[x, y] = ((x * 3) % 256, (y * 3) % 256, (x + y) % 256)
    im.save(path)


class _ImageBuilder:
    """A minimal Builder that writes one PNG into staging (no LLM)."""

    id = "img-builder"

    def __init__(self, *, size=(128, 128), blank=False):
        self._size, self._blank = size, blank

    def build(self, packet):
        root = Path(packet.writable_root)
        root.mkdir(parents=True, exist_ok=True)
        _draw(root / "building.png", size=self._size, blank=self._blank)
        (root / "decision_log.jsonl").write_text('{"step":"draw"}\n')
        return BuildResult(BuildStatus.COMPLETED, str(root), notes="image builder")


# --- certification: real checks earn their Stage-A slot -------------------------------


def test_all_default_checks_certify():
    reg = default_registry(Path.cwd() / "run" / "test_lock_certify")
    ids = {c.id for c in reg.certified_checks()}
    assert {"non_empty_artifact", "python_syntax", "json_valid"} <= ids
    # image checks certify wherever Pillow is present (it is here)
    assert {"image_loadable", "image_min_resolution", "image_not_blank"} <= ids


def test_cost_tiering_static_before_structural_before_dynamic():
    reg = default_registry(Path.cwd() / "run" / "test_lock_cost")
    costs = [int(cost_of(c)) for c in reg.certified_checks()]
    assert costs == sorted(costs), "certified checks must be ordered by ascending cost tier"
    by_id = {c.id: cost_of(c) for c in reg.certified_checks()}
    assert by_id["python_syntax"] == CheckCost.STATIC
    assert by_id["image_not_blank"] == CheckCost.DYNAMIC
    assert by_id["python_syntax"] < by_id["image_not_blank"]


def test_python_syntax_check_catches_broken_source():
    assert certify(PythonSyntaxCheck()).certified


def test_json_valid_check_catches_broken_json():
    assert certify(JsonValidCheck()).certified


# --- run behaviour --------------------------------------------------------------------


def test_python_syntax_fails_bad_passes_good(tmp_path):
    chk = PythonSyntaxCheck()
    good = tmp_path / "good"; good.mkdir()
    (good / "m.py").write_text("x = 1\n")
    assert chk.run(good, make_ticket()).result == Result.PASS
    bad = tmp_path / "bad"; bad.mkdir()
    (bad / "m.py").write_text("def f(:\n")
    assert chk.run(bad, make_ticket()).result == Result.FAIL


def test_code_checks_fail_not_crash_on_unparseable_files(tmp_path):
    # A check must be a total function: a pathological builder file is a clean FAIL, never an
    # exception that crashes the loop (harness-mod-7).
    py = tmp_path / "py"; py.mkdir()
    (py / "nul.py").write_text("x = 1\x00\n")            # null byte -> ast.parse raises ValueError
    assert PythonSyntaxCheck().run(py, make_ticket()).result == Result.FAIL

    py2 = tmp_path / "py2"; py2.mkdir()
    (py2 / "bin.py").write_bytes(b"\xff\xfe\x00\x01")    # not decodable as UTF-8 text
    assert PythonSyntaxCheck().run(py2, make_ticket()).result == Result.FAIL

    js = tmp_path / "js"; js.mkdir()
    (js / "bin.json").write_bytes(b"\xff\xfe\x00\x01")
    assert JsonValidCheck().run(js, make_ticket()).result == Result.FAIL


def test_checks_skip_when_not_applicable(tmp_path):
    # A text-only artifact: code + image checks SKIP, non_empty passes.
    art = tmp_path / "art"; art.mkdir()
    (art / "artifact.txt").write_text("a low-poly bakery")
    reg = default_registry(tmp_path / "lock")
    results = {r.check_id: r.result for r in reg.run_stage_a(art, make_ticket())}
    assert results["non_empty_artifact"] == Result.PASS
    assert results["python_syntax"] == Result.SKIP
    assert results["image_loadable"] == Result.SKIP


def test_stage_a_fail_fast_skips_expensive_dynamic_check(tmp_path):
    # Cheap STATIC python_syntax fails; the DYNAMIC pixel check must never run behind it.
    art = tmp_path / "art"; art.mkdir()
    (art / "broken.py").write_text("def f(:\n")
    _draw(art / "blank.png", blank=True)  # would also fail image_not_blank if reached
    reg = default_registry(tmp_path / "lock")
    results = reg.run_stage_a(art, make_ticket())
    ran = [r.check_id for r in results]
    assert "python_syntax" in ran and results[-1].result == Result.FAIL
    assert "image_not_blank" not in ran, "expensive DYNAMIC check ran after a cheap FAIL"


def test_blank_image_is_rejected(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    _draw(art / "flat.png", blank=True)
    reg = default_registry(tmp_path / "lock")
    results = {r.check_id: r for r in reg.run_stage_a(art, make_ticket())}
    assert results["image_not_blank"].result == Result.FAIL


def test_tiny_image_is_rejected(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    _draw(art / "tiny.png", size=(8, 8))
    reg = default_registry(tmp_path / "lock")
    # min-resolution is STRUCTURAL and runs before the DYNAMIC not-blank check
    results = reg.run_stage_a(art, make_ticket())
    ids = {r.check_id: r.result for r in results}
    assert ids.get("image_min_resolution") == Result.FAIL


# --- real metrics -> ratchet floors ---------------------------------------------------


def test_real_image_metrics_minted_as_floors(git_repo, registry, gatekeeper, tmp_path):
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=_ImageBuilder(size=(128, 128)), reviewer=StubReviewer(lambda r: True),
    )
    result = loop.run_ticket(make_ticket())
    assert result.committed, result.reason
    floors = gatekeeper.ratchet.floors()
    dim_keys = [k for k in floors if k.endswith(".image_min_dim")]
    std_keys = [k for k in floors if k.endswith(".image_min_stddev")]
    assert dim_keys and floors[dim_keys[0]] >= 32.0
    assert std_keys and floors[std_keys[0]] > 2.0


def test_image_accept_then_shrink_regresses(git_repo, registry, gatekeeper, tmp_path):
    # Accept a 128px image, then corrupt the committed artifact to blank -> ratchet catches it.
    from harness.gatekeeper import run_regression_suite
    loop = _make_loop(
        git_repo, registry, gatekeeper, tmp_path,
        builder=_ImageBuilder(size=(128, 128)), reviewer=StubReviewer(lambda r: True),
    )
    assert loop.run_ticket(make_ticket()).committed
    assert run_regression_suite(gatekeeper, registry) == []
    accepted = git_repo / "game" / "accepted" / "T-0001" / "building.png"
    _draw(accepted, blank=True)  # reintroduce "blank art" defect in the committed tree
    regressions = run_regression_suite(gatekeeper, registry)
    assert any("T-0001" in r for r in regressions)


def test_no_certified_check_is_kind_skipped(tmp_path):
    # REGRESSION (harness-mod-50): a check's `targets` are matched against ticket.KIND (registry._applies),
    # NOT filenames. A check with kind-mismatched targets (e.g. ["*.py"]) is silently SKIPPED for EVERY
    # ticket -> its gate never fires live. Every certified check must apply to every real ticket kind.
    from harness.checks.builtin import default_registry
    from harness.checks.registry import _applies
    from harness.models import Ticket, TicketKind
    from game.godot.checks import GodotParseCheck, GodotRenderCheck
    reg = default_registry(tmp_path / "lock")
    reg.register(GodotParseCheck())
    reg.register(GodotRenderCheck())
    reg.certify_all()
    for check in reg.certified_checks():
        for kind in TicketKind:
            t = Ticket(id="x", title="x", kind=kind, acceptance_criteria=[])
            assert _applies(check, t), (check.id, kind.name)   # certified but kind-skipped == a dead gate


def test_no_stub_content_check_certifies():
    from harness.checks.code import NoStubContentCheck
    assert certify(NoStubContentCheck()).certified


def test_no_stub_content_fails_compiling_stubs_passes_real(tmp_path):
    # the new gate lever (harness-mod-66): a stub that COMPILES (python_syntax passes it) must still FAIL,
    # while real code -- incl. `<`/`>` comparisons and real classes -- must PASS (no false positives).
    from harness.checks.code import NoStubContentCheck
    chk = NoStubContentCheck()
    real = tmp_path / 'real'; real.mkdir()
    (real / 'm.py').write_text('def f(x):' + chr(10) + '    return x + 1' + chr(10))
    assert chk.run(real, make_ticket()).result == Result.PASS
    stubs = [
        'def f():' + chr(10) + '    # YOUR CODE HERE' + chr(10) + '    pass' + chr(10),
        'x = 1' + chr(10) + '<code>' + chr(10),
        'def f():' + chr(10) + '    # TODO: implement' + chr(10) + '    pass' + chr(10),
    ]
    for i, stub in enumerate(stubs):
        d = tmp_path / ('stub%d' % i); d.mkdir()
        (d / 'm.py').write_text(stub)
        assert chk.run(d, make_ticket()).result == Result.FAIL, stub
    ok = tmp_path / 'ok'; ok.mkdir()
    (ok / 'm.py').write_text('y = a < b > c' + chr(10) + 'class K:' + chr(10) + '    def m(self):' + chr(10) + '        return 5' + chr(10))
    assert chk.run(ok, make_ticket()).result == Result.PASS
