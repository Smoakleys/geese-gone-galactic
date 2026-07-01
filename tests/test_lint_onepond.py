"""Tests for the One Pond Stage-A lint tool (`scripts/lint_onepond.py`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import lint_onepond


def _write(tmp_path: Path, config: dict) -> Path:
    p = tmp_path / "onepond_config.json"
    p.write_text(json.dumps(config))
    return p


def test_lint_passes_a_valid_pond(tmp_path, capsys):
    good = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 1, "y": 0}]}
    assert lint_onepond.lint(_write(tmp_path, good)) == 0
    assert "Stage A: PASS" in capsys.readouterr().out


def test_lint_fails_an_insolvent_pond(tmp_path, capsys):
    doomed = {"grid": [8, 8], "start_bread": 8, "buildings": [
        {"type": "hatchery", "x": 0, "y": 0}]}  # eats bread, no producer
    assert lint_onepond.lint(_write(tmp_path, doomed)) == 1
    out = capsys.readouterr().out
    assert "Stage A: FAIL" in out and "onepond_economy_solvent" in out


def test_lint_fails_a_scattered_pond(tmp_path, capsys):
    scattered = {"grid": [8, 8], "start_bread": 12, "buildings": [
        {"type": "bakery", "x": 0, "y": 0}, {"type": "bakery", "x": 7, "y": 7}]}
    assert lint_onepond.lint(_write(tmp_path, scattered)) == 1
    assert "auto_cohesion_check" in capsys.readouterr().out


def test_lint_reports_missing_file(tmp_path):
    assert lint_onepond.lint(tmp_path / "nope.json") == 2
