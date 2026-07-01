#!/usr/bin/env python3
"""Stop hook — enforce the autonomous 'do not stop' mandate structurally.

Claude Code runs this whenever the agent tries to END its turn. The failure this
fixes: 'keep going' was a prose instruction the model could rationalize its way
out of, because the continuation decision lived inside the thing that was failing.
This hook moves that decision OUT of the model: unless autonomous mode is off (or
the kill switch is set), it returns ``decision=block`` with a resume instruction,
so the harness — not the model's in-the-moment judgement — forces the next turn.

State (both live under ops/, both gitignored so they never leak into a clone):
  * ops/AUTOPILOT_ON  — presence = enforced autonomous mode. Absent by default, so
    ordinary interactive sessions are NOT trapped. The driver / resume prompt
    creates it to begin driving.
  * ops/STOP          — the kill switch. Presence ends autonomous mode immediately,
    even if AUTOPILOT_ON is still there. `touch ops/STOP` to reclaim control.

Fail-safe: on ANY error, or any unexpected state, we ALLOW the stop (never trap a
session because of a bug in this hook).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # .claude/hooks/keep_going.py -> repo root
STOP = REPO / "ops" / "STOP"
AUTOPILOT_ON = REPO / "ops" / "AUTOPILOT_ON"

RESUME = (
    "AUTONOMOUS MANDATE — DO NOT STOP. You are mid-way through the unattended GGG "
    "harness build (memory: ggg-autonomous-mandate). A summary, a status report, or "
    "'no more obvious work' is NOT a stopping point. Continue now: if you haven't run "
    "`python -m pytest tests/ -q` this turn, run it; read docs/HANDOFF.md and "
    "ops/backlog.md; then pick the next highest-value increment and ADVANCE it via "
    "branch -> test -> PR -> merge (GitHub API; gh is not installed). Never wait for "
    "the user. The ONLY valid stops are: the ops/STOP kill switch exists, or Bridger "
    "explicitly says stop. Take the next concrete action in THIS turn."
)


def _allow_stop() -> int:
    # Emit nothing actionable; exit 0 lets Claude Code end the turn normally.
    return 0


def main() -> int:
    try:
        # Read (and ignore) the hook payload; presence of stop_hook_active is fine —
        # the intentional drive loop does real work each turn, gated by the sentinels.
        try:
            json.load(sys.stdin)
        except Exception:
            pass

        if STOP.exists():
            return _allow_stop()               # kill switch wins
        if not AUTOPILOT_ON.exists():
            return _allow_stop()               # not in autonomous mode

        print(json.dumps({"decision": "block", "reason": RESUME}))
        return 0
    except Exception:
        return _allow_stop()                    # never trap a session on a hook bug


if __name__ == "__main__":
    sys.exit(main())
