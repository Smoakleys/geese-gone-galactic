"""Certification + behavior tests for the Godot engine checks.

Skipped when no Godot binary is installed (e.g. a CI box without ops/bin), so the suite stays
green off the workstation; on the workstation these run against the real engine.
"""

from __future__ import annotations

import pytest

from game.godot.binary import godot_path
from game.godot.checks import GodotParseCheck, GodotRenderCheck
from harness.checks.registry import certify
from harness.models import Result, Ticket, TicketKind

pytestmark = pytest.mark.skipif(godot_path() is None, reason="Godot binary not installed")


def _ticket() -> Ticket:
    return Ticket(id="t", title="t", kind=TicketKind.MIXED, acceptance_criteria=[])


def test_godot_parse_certifies():
    outcome = certify(GodotParseCheck())
    assert outcome.certified, outcome.reason


def test_godot_parse_passes_good_fails_bad():
    chk = GodotParseCheck()
    good = chk.run(chk.good_fixtures[0], _ticket())
    assert good.result == Result.PASS, good.evidence
    assert good.metrics.get("godot_scripts_parsed", 0) >= 1.0
    bad = chk.run(chk.bad_fixtures[0], _ticket())
    assert bad.result == Result.FAIL, bad.evidence


def test_godot_parse_skips_when_no_scripts(tmp_path):
    res = GodotParseCheck().run(tmp_path, _ticket())
    assert res.result == Result.SKIP


def test_godot_render_certifies():
    outcome = certify(GodotRenderCheck())
    assert outcome.certified, outcome.reason


def test_godot_render_passes_good_fails_bad():
    chk = GodotRenderCheck()
    good = chk.run(chk.good_fixtures[0], _ticket())
    assert good.result == Result.PASS, good.evidence
    assert good.metrics.get("green_fraction", 0) >= 0.08   # visible green land (region-based, not mean)
    bad = chk.run(chk.bad_fixtures[0], _ticket())   # parses, but renders nothing
    assert bad.result == Result.FAIL, bad.evidence


def test_godot_render_skips_when_no_scene(tmp_path):
    res = GodotRenderCheck().run(tmp_path, _ticket())
    assert res.result == Result.SKIP


def test_render_composes_raw_templated_content(tmp_path):
    # Self-verify on the FAST path: Icarus writes content.gd (a `func build`, no camera) which can't render
    # standalone. render_gdscript now composes it first, so Icarus can render+see its templated scene
    # mid-loop instead of building blind until post-build composition.
    from game.godot.capture import render_gdscript
    content = tmp_path / "content.gd"
    content.write_text("func build(root):\n\tadd_plane(root, Vector2(16, 16), Color.GREEN)\n"
                       "\tadd_sphere(root, 0.8, Color.WHITE, Vector3(0, 0.8, 0))\n")
    ok, detail = render_gdscript(content, tmp_path / "out.png")
    assert ok, detail
    assert (tmp_path / "out.png").exists()


def test_godot_render_fails_on_runtime_script_error(tmp_path):
    # A scene that crashes mid-_ready() (here: treating add_plane's void return as a node) still emits a
    # PARTIAL png at rc=0; the gate must FAIL it on the logged SCRIPT ERROR, not pass the half-built frame.
    from game.godot.scene_template import compose_scene
    scene = compose_scene(
        "func build(root):\n"
        "\tadd_plane(root, Vector2(16, 16), Color.GREEN)\n"
        "\tvar p = add_plane(root, Vector2(6, 6), Color.BLUE, 0.1)\n"
        "\tp.translation = Vector3(1, 0, 0)\n"        # p is null (add_plane returns void) -> runtime error
    )
    (tmp_path / "scene.gd").write_text(scene)
    res = GodotRenderCheck().run(tmp_path, _ticket())
    assert res.result == Result.FAIL, res.evidence
    assert "runtime error" in res.evidence


def test_godot_render_fails_degenerate_land_only_scene(tmp_path):
    # A scene that renders ONLY green land (no pond/building/goose) is degenerate and must FAIL, even
    # though it clears the green-fraction floor -- the distinct-scene-colours bar catches it.
    from game.godot.scene_template import compose_scene
    scene = compose_scene("func build(root):\n\tadd_plane(root, Vector2(16, 16), Color.GREEN)\n")
    (tmp_path / "scene.gd").write_text(scene)
    res = GodotRenderCheck().run(tmp_path, _ticket())
    assert res.result == Result.FAIL, res.evidence
    assert "degenerate" in res.evidence


def test_canonical_one_pond_scene_parses_and_renders(tmp_path):
    # The repo's canonical Icarus-built One Pond scene must always clear both certified gates.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "one_pond.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_full_multi_building_pond_scene_parses_and_renders(tmp_path):
    # The full pond scene (land + water + several buildings), composed from the pond_scene bridge.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "one_pond_full.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_goose_pond_scene_parses_and_renders(tmp_path):
    # OP-24: the pond with a GOOSE (Icarus-built via the render path) must clear both certified gates.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "goose_pond.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_flock_pond_scene_parses_and_renders(tmp_path):
    # OP-25: the pond with a FLOCK of three geese must clear both certified gates.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "flock_pond.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_world_pond_scene_parses_and_renders(tmp_path):
    # OP-26: the COMPLETE world (pond + bakery + nest + geese) must clear both certified gates.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "world_pond.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_detail_goose_pond_scene_parses_and_renders(tmp_path):
    # OP-34: a more detailed low-poly goose (body + neck + head + beak + tail) must clear both gates.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "detail_goose_pond.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_detail_flock_scene_parses_and_renders(tmp_path):
    # OP-36: two detailed lit geese by the pond, built first-try through the fully-improved harness.
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "detail_flock.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence


def test_detail_world_scene_parses_and_renders(tmp_path):
    # OP-35: the complete world (pond + bakery + nest + a detailed goose), lit; must clear both gates
    # (and, post PR #283, the render check verifies it did not crash mid-_ready with a SCRIPT ERROR).
    from pathlib import Path
    asset = Path(__file__).resolve().parents[1] / "game" / "godot" / "scenes" / "detail_world.gd"
    (tmp_path / "scene.gd").write_text(asset.read_text())
    assert GodotParseCheck().run(tmp_path, _ticket()).result == Result.PASS
    render = GodotRenderCheck().run(tmp_path, _ticket())
    assert render.result == Result.PASS, render.evidence
