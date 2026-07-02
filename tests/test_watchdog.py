"""Tests for the staleness watchdog policy + alerting."""

from __future__ import annotations

import json
import time

from control.store import RunStore
from ops.watchdog import check_once, decide


def test_decide_policy():
    # no heartbeat yet -> never alert
    assert decide(None, 1800, False) == (False, False)
    # fresh -> no alert, re-armed
    assert decide(100, 1800, False) == (False, False)
    # crossed into stale, not yet alerted -> alert now, mark alerted
    assert decide(2000, 1800, False) == (True, True)
    # still stale, already alerted -> do not re-alert
    assert decide(2000, 1800, True) == (False, True)
    # activity resumed -> re-arm (so the next episode alerts again)
    assert decide(100, 1800, True) == (False, False)


def test_check_once_alerts_when_stale(tmp_path):
    store = tmp_path / "state.json"
    RunStore(store).beat()
    d = json.loads(store.read_text())
    d["heartbeat"] = time.time() - 9999  # backdate: long-silent
    store.write_text(json.dumps(d))
    calls = []
    new_state = check_once(store, threshold=60.0, already_alerted=False, alert=calls.append)
    assert new_state is True
    assert calls and "STALE" in calls[0]


def test_check_once_quiet_when_fresh(tmp_path):
    store = tmp_path / "state.json"
    RunStore(store).beat()
    calls = []
    new_state = check_once(store, threshold=1800.0, already_alerted=False, alert=calls.append)
    assert new_state is False
    assert not calls
