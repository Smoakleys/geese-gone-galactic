"""End-to-end test of the ops entrypoint itself — the "turn it on and walk away" program.

The runner and every seam are unit-tested, but `scripts/run_onepond_autopilot.py:main` — the
thing an operator actually invokes — was only exercised by hand. This runs it in a throwaway
workspace and asserts the whole wiring holds: arg parsing, the certified registry, the visual
reviewer, the run to acceptance, the Stage-C harvest, and the post-build cold audit all the way
to a 0 exit code. A regression in the glue (not the units) is caught here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_autopilot_main_runs_to_clean_acceptance(tmp_path, capsys):
    pytest.importorskip("PIL")
    import run_onepond_autopilot as autopilot

    ws = tmp_path / "ws"
    rc = autopilot.main(["--workdir", str(ws)])
    assert rc == 0, "the autopilot must run to full acceptance with a clean cold audit"

    out = capsys.readouterr().out
    assert "accepted: 6/6" in out and "autonomy_rate: 100%" in out
    assert "cold audit clean" in out

    # Every ticket's config was really committed to the protected tree.
    for tid in ("T-POND-01", "T-POND-02", "T-POND-03", "T-POND-04", "T-POND-05", "T-POND-06"):
        assert (ws / "game" / "accepted" / tid / "onepond_config.json").exists()


def test_autopilot_main_audit_off_still_accepts(tmp_path):
    pytest.importorskip("PIL")
    import run_onepond_autopilot as autopilot

    rc = autopilot.main(["--workdir", str(tmp_path / "ws2"), "--audit-every", "0"])
    assert rc == 0  # periodic audit disabled; the post-build audit still runs and is clean
