"""Push a live 'what's happening now' status into the control store the remote site serves.

The dashboard reads a ``RunStore``; the autopilot populates the rich run data (accepted,
autonomy, floors, proposals, audit), but between/around runs the Owner still wants the site to
show what Claude is *currently* doing. This writes a small live-status block (activity + test
count + last change + timestamp) and beats the heartbeat, so the site stays populated and fresh.

Call it each increment:  ``python ops/status.py "building soldier-goose training"``
The default store path matches ``ops/serve_remote.py`` so the running site picks it up live.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

DEFAULT_STORE = _REPO / ".autopilot" / ".harness" / "state.json"


def update(activity: str, store_path: Optional[Path] = None) -> dict:
    """Write the live status (activity + derived test count + last git change + time). Returns it."""
    from control.store import RunStore
    from ops import notify  # reuse the digest's git/test-count helpers

    repo = _REPO
    status = {
        "activity": activity,
        "tests": notify._current_test_count(repo) or "",
        "last_change": _head_subject(repo),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = Path(store_path) if store_path else DEFAULT_STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    RunStore(path).record_status(status)
    return status


def _head_subject(repo: Path) -> str:
    from ops import notify
    try:
        return notify._git(repo, "log", "-1", "--pretty=%s")
    except Exception:
        return ""


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('usage: python ops/status.py "<current activity>"')
        return 2
    s = update(" ".join(argv))
    print(f"[status] {s['activity']}  ({s['tests']} tests, last: {s['last_change']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
