"""Staleness watchdog — the 'you'll KNOW when I'm down' failsafe.

Runs independently of Claude's session, polling the RunStore heartbeat (which `ops/status.py` beats
every increment). If there's been no activity for longer than a threshold, it emails the Owner ONE
alert per stale episode (re-arming once activity resumes), so a silent/stuck/crashed harness surfaces
to the Owner instead of going unnoticed. Pair it with the control site (Start/Pause/Stop).

    python ops/watchdog.py --threshold 1800 --interval 300      # alert if silent > 30 min
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable, Optional

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

DEFAULT_STORE = _REPO / ".autopilot" / ".harness" / "state.json"


def decide(age: Optional[float], threshold: float, already_alerted: bool) -> "tuple[bool, bool]":
    """Pure policy: given heartbeat age, return (send_alert_now, new_already_alerted_state).

    Alert exactly once when we cross into 'stale', and re-arm (so we alert again next episode) as
    soon as activity resumes (age back under threshold). No heartbeat yet -> do nothing."""
    if age is None:
        return False, already_alerted
    if age > threshold:
        return (not already_alerted), True
    return False, False  # fresh -> re-arm


def check_once(store_path, threshold: float, already_alerted: bool,
               alert: "Optional[Callable[[str], object]]" = None) -> bool:
    from control.store import RunStore
    from ops import notify
    alert = alert or notify.send_alert
    age = RunStore(Path(store_path)).heartbeat_age()
    send, new_state = decide(age, threshold, already_alerted)
    if send:
        mins = (age or 0) / 60.0
        alert(f"GGG harness looks STALE: no activity for {mins:.0f} min "
              f"(heartbeat age {age:.0f}s > {threshold:.0f}s threshold). Claude may be down or stuck "
              f"- open the control site to Start/Stop.")
        print(f"[watchdog] STALE alert sent (age {age:.0f}s)")
    return new_state


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Alert the Owner when the harness goes silent.")
    ap.add_argument("--store", default=str(DEFAULT_STORE))
    ap.add_argument("--threshold", type=float, default=1800.0, help="seconds of silence before alert")
    ap.add_argument("--interval", type=float, default=300.0, help="seconds between checks")
    ap.add_argument("--once", action="store_true", help="check a single time and exit")
    args = ap.parse_args(argv)
    print(f"[watchdog] watching {args.store} (alert if silent > {args.threshold:.0f}s)")
    alerted = False
    while True:
        try:
            alerted = check_once(args.store, args.threshold, alerted)
        except Exception as e:  # a watchdog that crashes is no watchdog — keep going
            print(f"[watchdog] check error: {e}")
        if args.once:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
