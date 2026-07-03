"""The command-driven One Pond demo (the 'talk to it' step)."""

from __future__ import annotations

from ops.play_commands import play


def test_commands_drive_the_pond():
    state = play(["build bakery", "build well", "event harvest", "tick", "tick", "status"], verbose=False)
    assert len(state["buildings"]) == 2                  # bakery + well placed
    assert state["bread"] == 46                          # 30 +10 harvest, then +3 +3 (1 bakery)


def test_command_demo_runs_as_a_script():
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(repo / "ops" / "play_commands.py")],
                       capture_output=True, text=True, cwd=str(repo), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "built bakery" in r.stdout and "Pond:" in r.stdout
