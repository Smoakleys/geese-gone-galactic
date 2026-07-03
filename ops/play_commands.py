"""Drive One Pond with text commands -- a step toward the plan's 'talk to it' (Jarvis) interface.

Each command is parsed by the Icarus-built `parse_command` and dispatched to the agent-built game modules:
  build <kind>   -- place a building at the next free grid cell
  event <name>   -- apply a pond event (harvest / fox / flood)
  tick           -- advance the economy one tick
  status         -- print a one-line status (bread, rank, safety)
  render <file>  -- render the CURRENT pond to a lit 3D PNG (needs Godot; skips gracefully without)
  save <file>    -- serialize the pond to a save string / load <file> -- restore it
  load <file>    -- restore a saved pond and keep playing
Commands here are scripted (this environment is non-interactive); the same loop takes live input.
Run: `python ops/play_commands.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.pond import (  # noqa: E402
    add_building, apply_event, parse_command, pond_rank, pond_score, pond_status, report, step,
)

GRID = 8
REACH = 2
_SLOTS = [(x, y) for y in range(GRID) for x in range(GRID)]


def play(commands: "list[str]", verbose: bool = True) -> dict:
    state: dict = {"bread": 30, "buildings": []}
    for text in commands:
        verb, target = parse_command(text)
        if verb == "build" and target:
            for x, y in _SLOTS:
                nxt = add_building(state, target, x, y, GRID)
                if len(nxt["buildings"]) > len(state["buildings"]):
                    state = nxt
                    break
            msg = f"built {target}"
        elif verb == "event" and target:
            state = apply_event(state, target)
            msg = f"event: {target} -> {state['bread']} bread"
        elif verb == "tick":
            state = step(state)
            msg = f"ticked -> {state['bread']} bread"
        elif verb == "status":
            st = pond_status(state, REACH)
            msg = report(state["bread"], pond_rank(pond_score(state)), st["safe"])
        elif verb == "render":
            # "see it": render the CURRENT pond to a lit 3D image (the command interface -> the renderer)
            from game.godot.pond_view import render_pond_state
            png = target or "pond.png"
            ok, detail = render_pond_state(state, png)
            msg = f"rendered -> {png}" if ok else f"render skipped: {detail}"
        elif verb == "save":
            from game.pond import serialize_pond
            path = Path(target or "pond.save")
            path.write_text(serialize_pond(state), encoding="utf-8")
            msg = f"saved -> {path}"
        elif verb == "load":
            from game.pond import deserialize_pond
            path = Path(target or "pond.save")
            if path.is_file():
                state = deserialize_pond(path.read_text(encoding="utf-8").strip())
                msg = f"loaded <- {path} ({state['bread']} bread, {len(state['buildings'])} buildings)"
            else:
                msg = f"no save file: {path}"
        else:
            msg = f"unknown command: {text!r}"
        if verbose:
            print(f"> {text:<16} {msg}")
    return state


if __name__ == "__main__":
    play(["build bakery", "build well", "event harvest", "tick", "tick", "status"])
