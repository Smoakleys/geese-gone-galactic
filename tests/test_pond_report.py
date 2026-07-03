"""Behaviour lock for the Icarus-built status report line (OP-18) -- exact string format."""

from __future__ import annotations

from game.pond.pond_report import report


def test_exact_report_format():
    assert report(14, "village", True) == "Pond: 14 bread, rank village, safe"
    assert report(0, "hamlet", False) == "Pond: 0 bread, rank hamlet, in danger"
    assert report(100, "city", True) == "Pond: 100 bread, rank city, safe"
