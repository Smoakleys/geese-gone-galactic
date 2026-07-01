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
    PlacementValidCheck,
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
    w = build_world({"start_bread": 14, "buildings": [
        {"type": "bakery", "x": 1, "y": 1}, {"type": "hatchery", "x": 2, "y": 1}]})
    w.tick(7)
    p = tmp_path / "save.json"
    w.save(p)
    assert World.load(p).to_dict() == w.to_dict()


# --- game checks ----------------------------------------------------------------------


def test_game_checks_certify():
    assert certify(PlacementValidCheck()).certified
    assert certify(EconomySolvencyCheck()).certified


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

    # The economy floor was minted to the ratchet, and the suite is regression-green.
    floors = gatekeeper.ratchet.floors()
    assert any(k.endswith(".onepond_min_bread") for k in floors)
    assert run_regression_suite(gatekeeper, registry) == []


def test_full_one_pond_has_all_three_buildings():
    # The final ticket assembles the complete pond: producer + consumer + storage.
    from game.onepond.tickets import POND_CONFIGS
    types = {b["type"] for b in POND_CONFIGS["T-POND-03"]["buildings"]}
    assert types == set(BUILDING_TYPES)
