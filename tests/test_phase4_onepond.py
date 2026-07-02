"""Phase 4 governance tests — "One Pond" built through the harness end-to-end.

This is the whole thesis under load: real game work (a bread economy with genuine failure
modes) authored by an Icarus stand-in, gated by deterministic game checks + a reviewer, and
committed only by the Gatekeeper. It also demonstrates the flywheel metric (autonomy rate) the
control surface reports (verification item 9).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from control.runner import AutonomousRunner
from control.store import RunStore
from game.onepond.checks import (
    EconomySolvencyCheck,
    LaunchViabilityCheck,
    PlacementValidCheck,
    PredatorSafetyCheck,
    WaterAccessCheck,
    build_onepond_registry,
)
from game.onepond.tickets import onepond_generation_client, onepond_tickets
from game.onepond.world import (
    BUILDING_TYPES,
    PlacementError,
    World,
    build_world,
    simulate_solvency,
)
from harness.checks.registry import certify, stage_a_passed
from harness.gatekeeper import Gatekeeper, run_regression_suite
from harness.icarus.llm_builder import LLMBuilder, ScriptedGenerationClient
from harness.models import Result
from harness.review.base import StubReviewer

from conftest import make_ticket


# --- world model ----------------------------------------------------------------------


def test_place_deducts_bread_and_occupies_cell():
    w = World(bread=10)
    w.place("hatchery", 2, 2)               # cost 6
    assert w.bread == 4
    ok, _ = w.can_place("bakery", 2, 2)     # occupied
    assert not ok


def test_illegal_placements_rejected():
    w = World(grid_w=4, grid_h=4, bread=10)
    for args in [("bakery", 9, 9), ("nope", 0, 0)]:
        with pytest.raises(PlacementError):
            w.place(*args)
    w.bread = 0
    with pytest.raises(PlacementError):        # unaffordable
        w.place("hatchery", 0, 0)


def test_tick_runs_bread_economy_and_caps_capacity():
    w = World(bread=5)
    w.place("bakery", 0, 0)                  # +3/tick
    w.tick(3)
    assert w.bread == 14 and w.tick_count == 3
    w.tick(100)
    assert w.bread <= w.capacity            # never exceeds storage capacity


def test_building_tiers_scale_output_and_cost():
    from game.onepond.world import MAX_TIER
    # A T2 bakery produces double bread; a T2 hatchery hatches double geese; cost scales too.
    w = build_world({"start_bread": 20, "buildings": [
        {"type": "bakery", "x": 0, "y": 0, "tier": 2},
        {"type": "hatchery", "x": 1, "y": 0, "tier": 2}]})
    assert w.net_bread_delta() == 3 * 2 + (-2 * 2)          # +2/tick
    assert w.bread == 20 - 6 * 2                             # T2 hatchery cost 2x
    w.tick(1)
    assert w.geese == 2                                      # T2 hatchery hatches 2/tick
    # Tier out of range is an illegal placement.
    for bad in (0, MAX_TIER + 1):
        with pytest.raises(PlacementError):
            build_world({"start_bread": 99, "buildings": [
                {"type": "bakery", "x": 0, "y": 0, "tier": bad}]})


def test_tier_round_trips_and_defaults_to_one(tmp_path):
    w = build_world({"start_bread": 20, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0, "tier": 3}]})
    assert w.buildings[0].tier == 1 and w.buildings[1].tier == 3   # default 1, explicit 3
    p = tmp_path / "s.json"; w.save(p)
    assert World.load(p).to_dict() == w.to_dict()                 # tier survives save/load


def test_placement_check_emits_total_tier_floor(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({"buildings": [
        {"type": "bakery", "x": 0, "y": 0, "tier": 2}, {"type": "granary", "x": 1, "y": 0}]}))
    res = PlacementValidCheck().run(art, make_ticket())
    assert res.result == Result.PASS and res.metrics["onepond_total_tier"] == 3  # 2 + 1


def test_solvency_reports_insolvency():
    solvent = simulate_solvency({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}]})
    assert solvent["solvent"] and solvent["net_delta"] == 3
    doomed = simulate_solvency({"start_bread": 12, "buildings": [
        {"type": "hatchery", "x": 0, "y": 0}]})
    assert not doomed["solvent"]


def test_save_load_round_trips(tmp_path):
    w = build_world({"start_bread": 16, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 2, "y": 1},
        {"type": "launchpad", "x": 3, "y": 1}]})
    w.tick(7)
    assert w.launched > 0                    # the run actually sent geese galactic
    p = tmp_path / "save.json"
    w.save(p)
    assert World.load(p).to_dict() == w.to_dict()


def test_launchpad_sends_geese_galactic():
    # A hatchery feeds a launchpad: every hatched goose is launched, so the flock stays ~0
    # while the launched score climbs one per tick.
    w = build_world({"start_bread": 16, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "launchpad", "x": 2, "y": 0}]})
    w.tick(10)
    assert w.launched == 10 and w.geese == 0
    # A launchpad with no hatchery has nothing to launch.
    idle = build_world({"start_bread": 16, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "launchpad", "x": 1, "y": 0}]})
    idle.tick(10)
    assert idle.launched == 0


def test_solvency_report_includes_launched():
    galactic = simulate_solvency({"start_bread": 16, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "launchpad", "x": 2, "y": 0}]})
    assert galactic["solvent"] and galactic["launched"] == 20
    grounded = simulate_solvency({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]})
    assert grounded["launched"] == 0


# --- game checks ----------------------------------------------------------------------


def test_game_checks_certify():
    assert certify(PlacementValidCheck()).certified
    assert certify(EconomySolvencyCheck()).certified
    assert certify(LaunchViabilityCheck()).certified
    assert certify(PredatorSafetyCheck()).certified
    assert certify(WaterAccessCheck()).certified


def test_launch_check_fails_dead_launchpad(tmp_path):
    # A launchpad with no hatchery feeding it launches nothing — dead infrastructure, blocked.
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({
        "start_bread": 12, "buildings": [
            {"type": "bakery", "x": 0, "y": 0}, {"type": "launchpad", "x": 1, "y": 0}]}))
    res = LaunchViabilityCheck().run(art, make_ticket())
    assert res.result == Result.FAIL and "space" in res.evidence


def test_launch_check_skips_pond_without_launchpad(tmp_path):
    # The early build-up ponds have no launchpad; launch viability is simply out of scope.
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({
        "start_bread": 12, "buildings": [
            {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}))
    assert LaunchViabilityCheck().run(art, make_ticket()).result == Result.SKIP


def test_launch_check_passes_and_mints_launched_metric(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({
        "start_bread": 16, "buildings": [
            {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
            {"type": "launchpad", "x": 2, "y": 0}]}))
    res = LaunchViabilityCheck().run(art, make_ticket())
    assert res.result == Result.PASS and res.metrics["onepond_launched"] > 0


def test_economy_check_fails_insolvent_config(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({
        "start_bread": 8, "buildings": [{"type": "hatchery", "x": 0, "y": 0}]}))
    res = EconomySolvencyCheck().run(art, make_ticket())
    assert res.result == Result.FAIL and "insolvent" in res.evidence


def test_placement_check_fails_overlap(tmp_path):
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({
        "buildings": [{"type": "bakery", "x": 1, "y": 1},
                      {"type": "bakery", "x": 1, "y": 1}]}))
    assert PlacementValidCheck().run(art, make_ticket()).result == Result.FAIL


def test_game_checks_are_total_on_malformed_but_valid_json(tmp_path):
    # A valid-JSON config with a malformed structure (buildings not a list of dicts) passes
    # json_valid but must be a clean Stage-A FAIL from the game checks, never an uncaught
    # TypeError/AttributeError crashing the loop (the harness-mod-7 total-function principle,
    # applied to game/onepond/checks.py).
    art = tmp_path / "art"; art.mkdir()
    (art / "onepond_config.json").write_text(json.dumps({"buildings": "oops"}))
    registry = build_onepond_registry(tmp_path / "lock")
    results = registry.run_stage_a(art, make_ticket("T-BAD"))  # must not raise
    assert not stage_a_passed(results)
    assert any(r.result == Result.FAIL for r in results)


# --- predator mechanic + safety check -------------------------------------------------


def test_predators_eat_unfenced_flock_and_fences_protect_it():
    # Un-fenced: two foxes eat the hatched geese as fast as they hatch — flock stays empty.
    exposed = build_world({"start_bread": 12, "predators": 2, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]})
    exposed.tick(10)
    assert exposed.geese == 0 and exposed.eaten == 10
    # Fenced one-for-one: the predators are neutralized and the flock grows normally.
    safe = build_world({"start_bread": 14, "predators": 2, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "fence", "x": 2, "y": 0}, {"type": "fence", "x": 3, "y": 0}]})
    safe.tick(10)
    assert safe.geese == 10 and safe.eaten == 0


def test_predator_free_ponds_are_unaffected():
    # The whole mechanic is opt-in: a config with no predators behaves exactly as before.
    w = build_world({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]})
    w.tick(10)
    assert w.geese == 10 and w.eaten == 0 and w.effective_predators == 0


def test_predator_safety_check_certifies_and_gates(tmp_path):
    assert certify(PredatorSafetyCheck()).certified

    def _run(config):
        art = tmp_path / "art"; art.mkdir(exist_ok=True)
        (art / "onepond_config.json").write_text(json.dumps(config))
        return PredatorSafetyCheck().run(art, make_ticket())

    # Predators + hatchery but under-fenced -> flock culled -> FAIL.
    assert _run({"start_bread": 12, "predators": 2, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "fence", "x": 2, "y": 0}]}).result == Result.FAIL
    # No predators declared -> out of scope -> SKIP.
    assert _run({"start_bread": 12, "predators": 0, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}).result == Result.SKIP
    # Predators fully fenced -> flock survives -> PASS + protected floor.
    ok = _run({"start_bread": 14, "predators": 2, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "fence", "x": 2, "y": 0}, {"type": "fence", "x": 3, "y": 0}]})
    assert ok.result == Result.PASS and ok.metrics["onepond_geese_protected"] > 0


def test_training_grounds_musters_soldiers():
    # A training grounds converts standing geese into soldier-geese each tick (tier-scaled).
    w = build_world({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "training_grounds", "x": 2, "y": 0}]})
    w.tick(5)
    assert w.soldiers == 5 and w.geese == 0            # each hatched goose is mustered
    # No training grounds -> no soldiers, geese accumulate as before.
    plain = build_world({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]})
    plain.tick(5)
    assert plain.soldiers == 0 and plain.geese == 5


def test_army_viable_check_certifies_and_gates(tmp_path):
    from game.onepond.checks import ArmyViableCheck
    assert certify(ArmyViableCheck()).certified

    def _run(config):
        art = tmp_path / "art"; art.mkdir(exist_ok=True)
        (art / "onepond_config.json").write_text(json.dumps(config))
        return ArmyViableCheck().run(art, make_ticket())

    # No training grounds -> out of scope -> SKIP.
    assert _run({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}).result == Result.SKIP
    # Training grounds but no hatchery to feed it -> empty muster -> FAIL.
    assert _run({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "training_grounds", "x": 1, "y": 0}]}).result == Result.FAIL
    # Hatchery feeds the training grounds -> army raised -> PASS + soldiers floor.
    ok = _run({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0},
        {"type": "training_grounds", "x": 2, "y": 0}]})
    assert ok.result == Result.PASS and ok.metrics["onepond_soldiers"] > 0


def test_command_wins_campaigns_by_spending_soldiers():
    from game.onepond.world import CAMPAIGN_COST
    w = build_world({"start_bread": 18, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 1, "y": 0},
        {"type": "hatchery", "x": 2, "y": 0}, {"type": "training_grounds", "x": 3, "y": 0},
        {"type": "command", "x": 4, "y": 0}]})
    w.tick(20)
    assert w.victories >= 1                         # soldiers were spent to win campaigns
    assert w.soldiers_total >= w.victories * CAMPAIGN_COST  # cumulative army covers the spend


def test_campaign_viable_check_certifies_and_gates(tmp_path):
    from game.onepond.checks import CampaignViableCheck
    assert certify(CampaignViableCheck()).certified

    def _run(config):
        art = tmp_path / "art"; art.mkdir(exist_ok=True)
        (art / "onepond_config.json").write_text(json.dumps(config))
        return CampaignViableCheck().run(art, make_ticket())

    # No command building -> out of scope -> SKIP.
    assert _run({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}).result == Result.SKIP
    # Command building but no soldiers to spend -> idle war room -> FAIL.
    assert _run({"start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "command", "x": 1, "y": 0}]}).result == Result.FAIL
    # Full pipeline feeds the command building -> campaigns won -> PASS + victories floor.
    ok = _run({"start_bread": 18, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 1, "y": 0},
        {"type": "hatchery", "x": 2, "y": 0}, {"type": "training_grounds", "x": 3, "y": 0},
        {"type": "command", "x": 4, "y": 0}]})
    assert ok.result == Result.PASS and ok.metrics["onepond_victories"] > 0


def test_water_access_check_certifies_and_gates(tmp_path):
    from game.onepond.checks import WaterAccessCheck
    assert certify(WaterAccessCheck()).certified

    def _run(config):
        art = tmp_path / "art"; art.mkdir(exist_ok=True)
        (art / "onepond_config.json").write_text(json.dumps(config))
        return WaterAccessCheck().run(art, make_ticket())

    # No well -> out of scope -> SKIP (the earlier tickets are unaffected).
    assert _run({"buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}).result == Result.SKIP
    # Well present but a hatchery is stranded far from it -> FAIL.
    assert _run({"buildings": [
        {"type": "hatchery", "x": 0, "y": 0}, {"type": "well", "x": 7, "y": 7}]}).result == Result.FAIL
    # Hatchery within reach of a well -> PASS + watered floor.
    ok = _run({"buildings": [
        {"type": "hatchery", "x": 0, "y": 0}, {"type": "well", "x": 1, "y": 1}]})
    assert ok.result == Result.PASS and ok.metrics["onepond_watered_hatcheries"] == 1


# --- render / visual gate on the game -------------------------------------------------


def test_stub_render_of_pond_passes_visual_gate(tmp_path):
    pytest.importorskip("PIL")
    from game.onepond.render import StubScreenshotWorker
    from harness.review.visual_gate import ReferenceAnchoredScorer
    config = {"grid": [8, 8], "start_bread": 14, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 3, "y": 2},
        {"type": "granary", "x": 5, "y": 4}]}
    out = StubScreenshotWorker().render(config, tmp_path / "pond.png")
    assert ReferenceAnchoredScorer().score(out).passed  # visual gate sees a real pond


def test_stub_render_of_sanctuary_pond_draws_fences_and_predators(tmp_path):
    pytest.importorskip("PIL")
    from game.onepond.render import StubScreenshotWorker, _PREDATOR
    from game.onepond.tickets import POND_CONFIGS
    from harness.review.visual_gate import ReferenceAnchoredScorer
    from PIL import Image

    out = StubScreenshotWorker().render(POND_CONFIGS["T-POND-05"], tmp_path / "sanctuary.png")
    assert ReferenceAnchoredScorer().score(out).passed  # the full sanctuary is visually gated too
    # The prowling foxes are actually drawn — a hazardous config *looks* hazardous.
    with Image.open(out) as im:
        colors = {c for _, c in im.convert("RGB").getcolors(maxcolors=1 << 24)}
    assert _PREDATOR in colors, "predator markers must appear in the render"


# --- visual reviewer (CV floor wired into Stage B) ------------------------------------


def _review_packet(config: dict, tid: str = "T-0001"):
    from harness.review.packet_builder import ReviewPacket
    from harness.models import Stage as _Stage
    t = make_ticket(tid)
    return t, ReviewPacket(
        ticket_id=t.id, criteria_hash=t.criteria_hash, stage=_Stage.B,
        criteria=t.criteria_for_stage(_Stage.B), rubric_text="", reference_paths=[],
        artifact_files={"onepond_config.json": json.dumps(config)})


def test_committed_reference_render_is_a_valid_pond_image():
    # The committed reference is load-bearing: the whole live visual gate anchors to it. Guard
    # it so a bad regeneration (corrupt/blank/wrong-size) is caught rather than silently
    # weakening the gate.
    pytest.importorskip("PIL")
    from game.onepond.review import _REFERENCE
    from harness.review.visual_gate import ReferenceAnchoredScorer, extract_signals
    assert _REFERENCE.exists()
    sig = extract_signals(_REFERENCE)
    assert sig.width == sig.height == 128           # the stub renderer's 8x8 pond canvas
    assert ReferenceAnchoredScorer().score(_REFERENCE).passed  # itself a real, non-blank pond


def test_visual_reviewer_is_reference_anchored(tmp_path):
    # The live visual gate scores against the committed canonical pond reference, not in a
    # vacuum: a real pond passes, but a structurally-fine yet off-palette render is rejected on
    # palette similarity (a signal the blank/tiny/noise floor alone would miss).
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    from game.onepond.review import _REFERENCE, OnePondVisualReviewer
    from harness.review.base import StubReviewer

    assert _REFERENCE.exists(), "the canonical reference render must be committed"

    class _OffPaletteWorker:
        id = "off-palette"

        def render(self, config, out_path):
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            im = Image.new("RGB", (128, 128), (20, 20, 140))  # blue bg, off the green palette
            d = ImageDraw.Draw(im)
            for i in range(9):
                x = 8 + i * 13
                d.line([(x, 8), (x, 120)], fill=(10, 10, 90))
            d.rectangle([40, 40, 84, 84], fill=(180, 60, 60), outline=(0, 0, 0))
            im.save(out_path)
            return out_path

    config = {"grid": [8, 8], "start_bread": 14, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 3, "y": 2}]}

    # Default stub render of a real pond matches the reference palette -> passes.
    t, packet = _review_packet(config)
    assert OnePondVisualReviewer(StubReviewer(lambda r: True),
                                 render_dir=tmp_path / "r1").review(packet, t).passed

    # Structurally fine but off-palette -> rejected specifically on reference similarity.
    off = OnePondVisualReviewer(StubReviewer(lambda r: True), worker=_OffPaletteWorker(),
                                render_dir=tmp_path / "r2")
    t2, packet2 = _review_packet(config)
    verdict = off.review(packet2, t2)
    assert not verdict.passed
    assert any("off-reference palette" in d.detail for d in verdict.defects)


def test_visual_reviewer_does_not_create_render_dir_until_used(tmp_path):
    # Resource hygiene: constructing a reviewer must not create its render dir eagerly.
    from game.onepond.review import OnePondVisualReviewer
    from harness.review.base import StubReviewer
    rd = tmp_path / "renders"
    OnePondVisualReviewer(StubReviewer(lambda x: True), render_dir=rd)
    assert not rd.exists()


def test_visual_reviewer_passes_real_pond_and_defers_to_base(tmp_path):
    pytest.importorskip("PIL")
    from game.onepond.review import OnePondVisualReviewer
    from harness.review.base import StubReviewer

    seen = []
    base = StubReviewer(lambda r: (seen.append(r) or True))
    reviewer = OnePondVisualReviewer(base, render_dir=tmp_path / "r")
    t, packet = _review_packet({"grid": [8, 8], "start_bread": 14, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 3, "y": 2},
        {"type": "granary", "x": 5, "y": 4}]})
    verdict = reviewer.review(packet, t)
    assert verdict.passed and seen, "a real pond passes the CV floor and reaches the base reviewer"


def test_visual_gate_over_consensus_is_the_full_stage_b_stack(tmp_path):
    # The production-shaped Stage B: the CV visual floor wrapping a multi-model unanimous
    # consensus. A real pond with agreeing models passes; the same pond with the visual gate
    # still passing but the models split is rejected fail-closed (unanimity is required).
    pytest.importorskip("PIL")
    from game.onepond.review import OnePondVisualReviewer
    from harness.review.consensus import ConsensusReviewer
    from harness.review.model_client import always_fail_client, always_pass_client

    config = {"grid": [8, 8], "start_bread": 14, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 3, "y": 2},
        {"type": "granary", "x": 5, "y": 4}]}

    agree = OnePondVisualReviewer(
        ConsensusReviewer([always_pass_client("m1"), always_pass_client("m2")]),
        render_dir=tmp_path / "r1")
    t, packet = _review_packet(config)
    assert agree.review(packet, t).passed  # visual floor + unanimous consensus -> PASS

    split = OnePondVisualReviewer(
        ConsensusReviewer([always_pass_client("m1"), always_fail_client("m2")]),
        render_dir=tmp_path / "r2")
    t2, packet2 = _review_packet(config)
    verdict = split.review(packet2, t2)
    assert not verdict.passed  # a real pond, but the models disagree -> fail-closed
    assert any("disagreement" in d.detail for d in verdict.defects)


def test_visual_reviewer_blocks_unreadable_pond_before_base(tmp_path):
    pytest.importorskip("PIL")
    from game.onepond.review import OnePondVisualReviewer
    from harness.review.base import StubReviewer

    seen = []
    base = StubReviewer(lambda r: (seen.append(r) or True))  # would pass — must never be consulted
    reviewer = OnePondVisualReviewer(base, render_dir=tmp_path / "r")
    # A 1x1 grid renders below the visual gate's minimum resolution: unreadable as a pond.
    t, packet = _review_packet({"grid": [1, 1], "start_bread": 10, "buildings": []})
    verdict = reviewer.review(packet, t)
    assert not verdict.passed and not seen, "the CV floor blocks before the subjective reviewer"
    assert any("visual gate" in d.detail for d in verdict.defects)


# --- end to end: the harness builds One Pond, unattended ------------------------------


def test_harness_builds_one_pond_end_to_end(git_repo, tmp_path):
    pytest.importorskip("PIL")  # the run is visually gated end-to-end
    from game.onepond.review import OnePondVisualReviewer
    registry = build_onepond_registry(tmp_path / "lock")
    gatekeeper = Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet")
    store = RunStore(tmp_path / "state.json")
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=OnePondVisualReviewer(StubReviewer(lambda r: True), render_dir=tmp_path / "renders"),
        icarus_builder=LLMBuilder(onepond_generation_client()),
        staging_root=tmp_path / "staging",
    )
    tickets = onepond_tickets()
    for t in tickets:
        runner.submit(t)
    records = runner.run_pending()

    assert len(records) == len(tickets)
    assert all(r.committed for r in records), [r.reason for r in records if not r.committed]
    assert store.autonomy_rate() == 1.0                       # zero escape-hatch: full autonomy
    assert store.metrics()["accepted"] == len(tickets)

    # Every committed config is a real, solvent pond.
    for t in tickets:
        cfg = git_repo / "game" / "accepted" / t.id / "onepond_config.json"
        assert cfg.exists()
        assert simulate_solvency(json.loads(cfg.read_text()))["solvent"]

    # The final sanctuary ticket sent geese galactic while fenced against predators.
    final = simulate_solvency(json.loads(
        (git_repo / "game" / "accepted" / "T-POND-05" / "onepond_config.json").read_text()))
    assert final["launched"] > 0 and final["predators"] > 0 and final["eaten"] == 0

    # Economy, galactic-score, living-flock, and predator-safety floors were all minted;
    # suite regression-green.
    floors = gatekeeper.ratchet.floors()
    assert any(k.endswith(".onepond_min_bread") for k in floors)
    assert any(k.endswith(".onepond_launched") for k in floors)
    assert any(k.endswith(".onepond_geese_hatched") for k in floors)   # liveliness ran as a live gate
    assert any(k.endswith(".onepond_geese_protected") for k in floors)  # predator safety ran too
    assert any(k.endswith(".onepond_watered_hatcheries") for k in floors)  # water access ran too
    assert any(k.endswith(".onepond_total_tier") for k in floors)          # tier progression floor
    assert any(k.endswith(".onepond_soldiers") for k in floors)            # army-viability ran too
    assert any(k.endswith(".onepond_victories") for k in floors)           # campaign-viability ran too
    assert run_regression_suite(gatekeeper, registry) == []

    # Cold audit (acceptance is not forever): re-verify the committed tree mechanically AND with
    # a fresh cold visual re-review of the committed bytes — must be clean.
    from harness.audit.cold_audit import cold_audit
    by_id = {t.id: t for t in tickets}
    audit = cold_audit(gatekeeper, registry,
                       reviewer=OnePondVisualReviewer(StubReviewer(lambda r: True),
                                                      render_dir=tmp_path / "audit_renders"),
                       ticket_provider=by_id.get)
    assert not audit.blocked, audit.summary()


def test_liveliness_gate_forces_rework_in_the_loop(git_repo, tmp_path):
    """The harvested check catches a real in-loop build and drives Icarus to fix it.

    Icarus first ships a lifeless pond (granary capacity, no hatchery). Stage A now rejects it
    on ``onepond_liveliness`` and hands that defect back; on rework Icarus adds a hatchery and
    the living pond is accepted. This is the flywheel closing on a live build, not a fixture.
    """
    lifeless = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "granary", "x": 1, "y": 0}]}
    living = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "granary", "x": 1, "y": 0},
        {"type": "hatchery", "x": 2, "y": 0}]}

    def script(packet):
        fixed = any(d.criterion == "onepond_liveliness" for d in packet.defects)
        return {"onepond_config.json": json.dumps(living if fixed else lifeless)}

    from harness.icarus.llm_builder import ScriptedGenerationClient
    registry = build_onepond_registry(tmp_path / "lock")
    gatekeeper = Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet")
    store = RunStore(tmp_path / "state.json")
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True),
        icarus_builder=LLMBuilder(ScriptedGenerationClient(script)),
        staging_root=tmp_path / "staging", max_rounds=4,
    )
    runner.submit(make_ticket("T-LIVE"))
    recs = runner.run_pending()

    assert recs[0].committed and recs[0].rounds >= 2   # rejected once, fixed on rework
    accepted = json.loads(
        (git_repo / "game" / "accepted" / "T-LIVE" / "onepond_config.json").read_text())
    assert any(b["type"] == "hatchery" for b in accepted["buildings"])   # Icarus added the flock
    assert simulate_solvency(accepted)["geese"] > 0                      # the accepted pond is alive


def test_escape_hatch_rescues_a_plateaued_one_pond_ticket(git_repo, tmp_path):
    # The "never block on a human" tooth on real game work: Icarus keeps shipping an insolvent
    # pond (Stage A economy check fails every round -> plateau), so the runner auto-escalates to
    # the escape-hatch builder, which ships a solvent pond that's accepted. No human is consulted.
    from control.runner import AutonomousRunner
    from control.store import RunStore
    registry = build_onepond_registry(tmp_path / "lock")
    gatekeeper = Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet")
    store = RunStore(tmp_path / "state.json")

    insolvent = {"grid": [8, 8], "start_bread": 8, "buildings": [
        {"type": "hatchery", "x": 0, "y": 0}]}                 # eats bread, no producer
    solvent = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "hatchery", "x": 1, "y": 0}]}
    stubborn = LLMBuilder(ScriptedGenerationClient(
        lambda p: {"onepond_config.json": json.dumps(insolvent)}))
    rescue = LLMBuilder(ScriptedGenerationClient(
        lambda p: {"onepond_config.json": json.dumps(solvent)}))

    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True), icarus_builder=stubborn,
        escape_hatch_builder=rescue, staging_root=tmp_path / "staging",
        plateau_window=2, max_rounds=5)
    runner.submit(make_ticket("T-RESCUE"))
    recs = runner.run_pending()

    assert recs[0].committed and recs[0].escape_hatch  # Icarus plateaued; the hatch rescued it
    assert store.autonomy_rate() == 0.0                # accepted, but only via the escape hatch
    accepted = json.loads(
        (git_repo / "game" / "accepted" / "T-RESCUE" / "onepond_config.json").read_text())
    assert simulate_solvency(accepted)["solvent"]      # a real, solvent pond was committed


def test_ticket_set_exercises_every_building_type():
    # As the game grows, the ticket set as a whole must exercise every building type at least
    # once (rather than pinning it to one 'final' pond that goes stale each time we add a type).
    from game.onepond.tickets import POND_CONFIGS
    used = {b["type"] for cfg in POND_CONFIGS.values() for b in cfg["buildings"]}
    assert used == set(BUILDING_TYPES)
