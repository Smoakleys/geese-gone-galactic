"""The command-driven One Pond demo (the 'talk to it' step)."""

from __future__ import annotations

from ops.play_commands import play


def test_commands_drive_the_pond():
    state = play(["build bakery", "build well", "event harvest", "tick", "tick", "status"], verbose=False)
    assert len(state["buildings"]) == 2                  # bakery + well placed
    assert state["bread"] == 46                          # 30 +10 harvest, then +3 +3 (1 bakery)


def test_render_command_is_handled(tmp_path):
    # the "see it" command connects the command interface to the renderer; handled with or without Godot.
    from game.godot.binary import godot_path
    png = tmp_path / "pond.png"
    state = play(["build bakery", f"render {png}"], verbose=False)
    assert len(state["buildings"]) == 1                  # the game still advanced normally
    if godot_path() is not None:
        assert png.exists()                              # with Godot, the current pond was rendered


def test_command_demo_runs_as_a_script():
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(repo / "ops" / "play_commands.py")],
                       capture_output=True, text=True, cwd=str(repo), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "built bakery" in r.stdout and "Pond:" in r.stdout


def test_save_and_load_commands_round_trip(tmp_path):
    # the command interface can persist + resume: build, save, then load into a fresh session recovers it.
    save = tmp_path / "pond.save"
    played = play(["build bakery", "build nest", f"save {save}"], verbose=False)
    assert save.exists()
    reloaded = play([f"load {save}", "tick"], verbose=False)   # fresh session loads the save, then ticks
    assert len(reloaded["buildings"]) == 2                      # bakery + nest recovered
    assert reloaded["bread"] == played["bread"] + 2             # continued from save: +3 bakery, -1 nest
