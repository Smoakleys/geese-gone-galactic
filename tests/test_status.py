"""Tests for the live-status feed that keeps the remote site populated (ops/status.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "ops"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from control.dashboard import render_html
from control.store import RunStore
import status as status_mod


def test_record_status_round_trips_and_beats(tmp_path):
    store = RunStore(tmp_path / "state.json")
    assert store.status() == {}
    store.record_status({"activity": "building tiers", "tests": "146"})
    assert store.status()["activity"] == "building tiers"
    assert store.snapshot()["status"]["tests"] == "146"
    assert store.heartbeat_age() is not None            # recording status beats the heartbeat


def test_dashboard_shows_live_activity(tmp_path):
    store = RunStore(tmp_path / "state.json")
    store.record_status({"activity": "mustering soldier-geese", "tests": "146",
                         "last_change": "Add soldier training", "updated": "now"})
    html = render_html(store)
    assert "mustering soldier-geese" in html and "146 tests" in html


def test_status_update_writes_activity_and_derived_fields(tmp_path):
    s = status_mod.update("resuming the build", store_path=tmp_path / "state.json")
    assert s["activity"] == "resuming the build"
    assert "updated" in s and s["updated"]
    assert RunStore(tmp_path / "state.json").status()["activity"] == "resuming the build"
