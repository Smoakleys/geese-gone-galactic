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
from harness.checks.registry import certify
from harness.gatekeeper import Gatekeeper, run_regression_suite
from harness.icarus.llm_builder import LLMBuilder
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


# --- end to end: the harness builds One Pond, unattended ------------------------------


def test_harness_builds_one_pond_end_to_end(git_repo, tmp_path):
    registry = build_onepond_registry(tmp_path / "lock")
    gatekeeper = Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet")
    store = RunStore(tmp_path / "state.json")
    runner = AutonomousRunner(
        store=store, repo_root=git_repo, registry=registry, gatekeeper=gatekeeper,
        reviewer=StubReviewer(lambda r: True),
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
    assert run_regression_suite(gatekeeper, registry) == []


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


def test_full_one_pond_has_all_building_types():
    # The final ticket assembles the complete galactic sanctuary: producer + consumer + storage
    # + launchpad + fence (against the predators it invites).
    from game.onepond.tickets import POND_CONFIGS
    types = {b["type"] for b in POND_CONFIGS["T-POND-05"]["buildings"]}
    assert types == set(BUILDING_TYPES)
