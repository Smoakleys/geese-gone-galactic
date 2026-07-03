"""Play a scripted One Pond game and print a readable transcript.

A runnable showcase of the Icarus-built game core (everything in `game.pond` was produced by the local
agent through the harness gate). It follows the hint system to build a thriving pond, printing the advice,
status, score, and outcome at each step. Run: `python ops/play_onepond.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.pond import (  # noqa: E402  (path set above)
    add_building, pond_advice, pond_outcome, pond_score, pond_status, step,
)

REACH = 2
GRID = 8
PLAN = [("bakery", 0, 0), ("well", 1, 0), ("granary", 0, 1), ("nest", 4, 4), ("fence", 4, 5)]


def _run(plan: "list[tuple[str, int, int]]", start_bread: int, verbose: bool) -> dict:
    state: dict = {"bread": start_bread, "buildings": []}
    for kind, x, y in plan:
        if verbose:
            print(f"  hint: {pond_advice(state, REACH):<15} | placing {kind} at ({x},{y})")
        state = add_building(state, kind, x, y, GRID)
    if verbose:
        print(f"  hint: {pond_advice(state, REACH)}")
        print("  --- running 3 ticks ---")
    for _ in range(3):
        state = step(state)
    if verbose:
        st = pond_status(state, REACH)
        print(f"  bread={state['bread']}  safe={st['safe']}  score={pond_score(state)}  "
              f"outcome={pond_outcome(state, REACH)}")
    return state


def play(verbose: bool = True) -> dict:
    """A well-built pond: follow the hints -> thriving."""
    if verbose:
        print("=== One Pond: a well-tended pond (built by Icarus) ===")
    return _run(PLAN, 20, verbose)


def play_neglected(verbose: bool = True) -> dict:
    """A neglected pond: a bakery with no well + an unfenced nest -> the hints warn, the outcome suffers."""
    if verbose:
        print("=== One Pond: a neglected pond ===")
    return _run([("bakery", 0, 0), ("nest", 5, 5)], 20, verbose)


if __name__ == "__main__":
    play()
    print()
    play_neglected()
