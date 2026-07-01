"""One full flywheel turn: a subjective Stage-B defect becomes a mechanical Stage-A gate.

Reviewers kept rejecting ponds that were legal and solvent yet "read as dead" — a granary
raising goose *capacity* for a flock that is never hatched. That judgement was subjective:
placement is legal, the economy is solvent, and with no launchpad the launch check does not
apply, so Stage A waved the pond through and a human/model reviewer had to catch it every time.

``onepond_liveliness`` closes that gap. These tests prove the turn end to end:

* the check certifies (green-on-good, red-on-bad) — so it earns its Stage-A slot;
* before it, a lifeless pond slips past every other certified gate (the gap the reviewer filled);
* after it, the same pond is rejected by Stage A mechanically — the reviewer never has to see it;
* a bare build-up pond (no granary) is legitimately out of scope and is not falsely flagged.
"""

from __future__ import annotations

import json
from pathlib import Path

from game.onepond.checks import (
    EconomySolvencyCheck,
    LaunchViabilityCheck,
    LivelinessCheck,
    PlacementValidCheck,
    build_onepond_registry,
)
from harness.checks.builtin import default_registry
from harness.checks.registry import certify, stage_a_passed
from harness.models import Result

from conftest import make_ticket

# A pond that is legal and solvent but lifeless: a granary buys goose capacity, yet with no
# hatchery not a single goose is ever hatched. This is exactly what reviewers kept rejecting.
LIFELESS_POND = {
    "grid": [8, 8], "start_bread": 12,
    "buildings": [{"type": "bakery", "x": 0, "y": 0},
                  {"type": "granary", "x": 1, "y": 0}],
}
# A minimal build-up pond: just a bakery. Legitimately not alive yet, and out of scope.
BARE_POND = {
    "grid": [8, 8], "start_bread": 12,
    "buildings": [{"type": "bakery", "x": 0, "y": 0}],
}
# A living pond: the granary's capacity is backed by a hatchery that keeps a real flock.
LIVING_POND = {
    "grid": [8, 8], "start_bread": 12,
    "buildings": [{"type": "bakery", "x": 0, "y": 0},
                  {"type": "hatchery", "x": 1, "y": 0},
                  {"type": "granary", "x": 2, "y": 0}],
}


def _artifact(tmp_path: Path, config: dict) -> Path:
    d = tmp_path / "artifact"
    d.mkdir(parents=True, exist_ok=True)
    (d / "onepond_config.json").write_text(json.dumps(config, indent=2, sort_keys=True))
    return d


def _pre_flywheel_registry(lock_dir: Path):
    """The registry as it was *before* liveliness was harvested: every other game check, certified."""
    reg = default_registry(lock_dir)
    reg.register(PlacementValidCheck())
    reg.register(EconomySolvencyCheck())
    reg.register(LaunchViabilityCheck())
    reg.certify_all()
    return reg


def test_liveliness_check_certifies():
    outcome = certify(LivelinessCheck())
    assert outcome.certified, outcome.reason  # green-on-good, red-on-bad -> earns its Stage-A slot


def test_lifeless_pond_slips_past_the_pre_flywheel_gates(tmp_path):
    reg = _pre_flywheel_registry(tmp_path / "lock")
    results = reg.run_stage_a(_artifact(tmp_path, LIFELESS_POND), make_ticket())
    assert stage_a_passed(results), "the lifeless pond must slip past — that's the gap Stage B filled"
    assert "onepond_liveliness" not in {r.check_id for r in results}


def test_liveliness_makes_the_subjective_defect_mechanical(tmp_path):
    reg = build_onepond_registry(tmp_path / "lock")  # now includes the harvested check
    results = reg.run_stage_a(_artifact(tmp_path, LIFELESS_POND), make_ticket())
    assert not stage_a_passed(results), "liveliness must now reject the lifeless pond in Stage A"
    liveliness = next(r for r in results if r.check_id == "onepond_liveliness")
    assert liveliness.result == Result.FAIL and "lifeless pond" in liveliness.evidence


def test_liveliness_passes_a_living_pond_and_mints_a_floor(tmp_path):
    reg = build_onepond_registry(tmp_path / "lock")
    results = reg.run_stage_a(_artifact(tmp_path, LIVING_POND), make_ticket())
    assert stage_a_passed(results)
    liveliness = next(r for r in results if r.check_id == "onepond_liveliness")
    assert liveliness.result == Result.PASS
    assert liveliness.metrics["onepond_geese_hatched"] >= 1  # becomes a per-ticket ratchet floor


def test_liveliness_skips_bare_buildup_pond(tmp_path):
    reg = build_onepond_registry(tmp_path / "lock")
    results = reg.run_stage_a(_artifact(tmp_path, BARE_POND), make_ticket())
    liveliness = next(r for r in results if r.check_id == "onepond_liveliness")
    assert liveliness.result == Result.SKIP  # a lone bakery is legitimately not yet alive
    assert stage_a_passed(results)           # not falsely flagged
