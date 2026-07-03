"""The One Pond demo runs and shows both outcomes (smoke test of the runnable showcase)."""

from __future__ import annotations

from ops.play_onepond import play, play_neglected
from game.pond import pond_outcome


def test_demo_well_tended_pond_thrives():
    state = play(verbose=False)
    assert len(state["buildings"]) == 5
    assert pond_outcome(state, 2) == "thriving"


def test_demo_neglected_pond_suffers():
    state = play_neglected(verbose=False)
    assert pond_outcome(state, 2) == "dry"        # a bakery with no well -> the stakes are real


def test_demo_runs_end_to_end_as_a_script():
    # the showcase must actually RUN (not just import) -- catches console/encoding crashes that import-only
    # tests miss (e.g. the cp1252 U+2212 crash). Runs `python ops/play_onepond.py` as a subprocess.
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(repo / "ops" / "play_onepond.py")],
                       capture_output=True, text=True, cwd=str(repo), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "thriving" in r.stdout and "dry" in r.stdout          # both scenarios printed
