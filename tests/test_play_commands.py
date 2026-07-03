"""The command-driven One Pond demo (the 'talk to it' step)."""

from __future__ import annotations

from ops.play_commands import play


def test_commands_drive_the_pond():
    state = play(["build bakery", "build well", "event harvest", "tick", "tick", "status"], verbose=False)
    assert len(state["buildings"]) == 2                  # bakery + well placed
    assert state["bread"] == 46                          # 30 +10 harvest, then +3 +3 (1 bakery)


def test_render_command_produces_art_by_default(tmp_path):
    # the "see it" command's DEFAULT look is now real painterly ART (compose_pond_art), no Godot needed.
    png = tmp_path / "pond.png"
    state = play(["build bakery", f"render {png}"], verbose=False)
    assert len(state["buildings"]) == 1                  # the game still advanced normally
    assert png.exists()                                  # render -> art (always produces the PNG)


def test_render3d_command_is_handled(tmp_path):
    # the older 3D primitive view is still reachable as `render3d` (skips gracefully without Godot).
    from game.godot.binary import godot_path
    png = tmp_path / "pond3d.png"
    state = play(["build bakery", f"render3d {png}"], verbose=False)
    assert len(state["buildings"]) == 1
    if godot_path() is not None:
        assert png.exists()


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


def test_run_command_dispatches_one_command():
    from ops.play_commands import run_command
    state = {"bread": 10, "buildings": []}
    state, msg = run_command(state, "build bakery")
    assert len(state["buildings"]) == 1 and "built bakery" in msg
    state, msg = run_command(state, "tick")
    assert state["bread"] == 13 and "ticked" in msg          # +3 bakery
    _, msg = run_command(state, "wobble")                     # unknown verb -> graceful message
    assert "unknown command" in msg


def test_interactive_loop_processes_commands_and_quits(monkeypatch, capsys):
    # cover the actual playable-game loop: fed commands via stdin, it processes each and exits on 'quit'.
    from ops import play_commands
    feed = iter(["build bakery", "tick", "status", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(feed))
    play_commands.interactive()
    out = capsys.readouterr().out
    assert "built bakery" in out and "ticked" in out and "Pond:" in out   # each command ran + printed


def test_art_command_renders_the_pond_as_art(tmp_path):
    # the `art` command composites the generated sprites for the current state into a PNG (the real look).
    out = tmp_path / "pond_art.png"
    played = play(["build bakery", "build nest", f"art {out}"], verbose=False)
    assert out.exists() and len(played["buildings"]) == 2


def test_load_of_a_corrupt_save_does_not_crash(tmp_path):
    # same bug class as the web game: a corrupt save must not crash the text game (found by probing).
    from ops.play_commands import run_command
    bad = tmp_path / "bad.save"
    bad.write_text("garbage not a pond")
    state = {"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}
    state, msg = run_command(state, f"load {bad}")               # must return, not raise
    assert "corrupt" in msg
    assert len(state["buildings"]) == 1                          # current pond preserved
