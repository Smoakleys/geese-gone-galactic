"""Drive One Pond with text commands -- a step toward the plan's 'talk to it' (Jarvis) interface.

Each command is parsed by the Icarus-built `parse_command` and dispatched to the agent-built game modules:
  build <kind>   -- place a building at the next free grid cell
  event <name>   -- apply a pond event (harvest / fox / flood)
  tick           -- advance the economy one tick
  status         -- print a one-line status (bread, rank, safety)
  render <file>  -- render the CURRENT pond to a lit 3D PNG (needs Godot; skips gracefully without)
  art <file>     -- render the CURRENT pond as painterly ART (composited generated sprites)
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


def run_command(state: dict, text: str) -> "tuple[dict, str]":
    """Process ONE command against ``state`` -> (new_state, message). The single dispatch shared by the
    scripted ``play`` and the interactive loop."""
    verb, target = parse_command(text)
    if verb == "build" and target:
        for x, y in _SLOTS:
            nxt = add_building(state, target, x, y, GRID)
            if len(nxt["buildings"]) > len(state["buildings"]):
                return nxt, f"built {target}"
        return state, f"no free cell for {target}"
    if verb == "event" and target:
        state = apply_event(state, target)
        return state, f"event: {target} -> {state['bread']} bread"
    if verb == "tick":
        state = step(state)
        return state, f"ticked -> {state['bread']} bread"
    if verb == "status":
        st = pond_status(state, REACH)
        return state, report(state["bread"], pond_rank(pond_score(state)), st["safe"])
    if verb == "render":
        from game.godot.pond_view import render_pond_state
        png = target or "pond.png"
        ok, detail = render_pond_state(state, png)
        return state, (f"rendered -> {png}" if ok else f"render skipped: {detail}")
    if verb == "art":
        # "see it as ART": composite the generated painterly sprites for the current pond (the real look)
        from game.art_view import compose_pond_art
        out = compose_pond_art(state, target or "pond_art.png")
        return state, f"art rendered -> {out}"
    if verb == "save":
        from game.pond import serialize_pond
        path = Path(target or "pond.save")
        path.write_text(serialize_pond(state), encoding="utf-8")
        return state, f"saved -> {path}"
    if verb == "load":
        from game.pond import deserialize_pond
        path = Path(target or "pond.save")
        if path.is_file():
            state = deserialize_pond(path.read_text(encoding="utf-8").strip())
            return state, f"loaded <- {path} ({state['bread']} bread, {len(state['buildings'])} buildings)"
        return state, f"no save file: {path}"
    return state, f"unknown command: {text!r}"


def play(commands: "list[str]", verbose: bool = True) -> dict:
    state: dict = {"bread": 30, "buildings": []}
    for text in commands:
        state, msg = run_command(state, text)
        if verbose:
            print(f"> {text:<16} {msg}")
    return state


def interactive() -> None:
    """Play One Pond by typing commands live. 'quit' exits. This is the actual playable game loop."""
    state: dict = {"bread": 30, "buildings": []}
    print("One Pond -- commands: build <kind> | event harvest/fox/flood | tick | status | "
          "render <file> | save/load <file> | quit")
    while True:
        try:
            line = input("pond> ").strip()
        except EOFError:
            break
        if line in ("quit", "exit"):
            break
        if line:
            state, msg = run_command(state, line)
            print(msg)


if __name__ == "__main__":
    import sys
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive()                       # play live: type commands
    else:
        play(["build bakery", "build well", "event harvest", "tick", "tick", "status"])   # scripted demo
