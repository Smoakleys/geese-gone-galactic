"""Certification + behavior tests for the Godot engine checks.

Skipped when no Godot binary is installed (e.g. a CI box without ops/bin), so the suite stays
green off the workstation; on the workstation these run against the real engine.
"""

from __future__ import annotations

import pytest

from game.godot.binary import godot_path
from game.godot.checks import GodotParseCheck
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
