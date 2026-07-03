# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-4 through the full pipeline
# (authored ticket -> agent -> python_syntax gate -> gatekeeper commit). Preserved as the agent produced
# it; behaviour locked by tests/test_pond_state.py. The One Pond simulation composing the economy + placement.
"""
One Pond simulation state management.

State format:
{
    'bread': int,
    'buildings': [
        {'kind': str, 'x': int, 'y': int},
        ...
    ]
}

Functions:
- step(state): advances the simulation by one tick.
  * Each building of kind 'bakery' adds 3 bread.
  * Each building of kind 'nest' subtracts 1 bread (bread never goes below 0).
  Returns the updated state.

- add_building(state, kind, x, y, n):
  Adds a building at coordinates (x, y) on an n-by-n grid if:
    * 0 <= x < n and 0 <= y < n
    * No existing building occupies that cell.
  If placement is invalid, the state remains unchanged.
  Returns the updated state.
"""

from __future__ import annotations

from typing import Dict, List

State = Dict[str, object]
Building = Dict[str, object]


def step(state: State) -> State:
    """Advance the simulation by one tick."""
    bread = state.get('bread', 0)
    buildings: List[Building] = state.get('buildings', [])

    # Count effects
    for b in buildings:
        kind = b.get('kind')
        if kind == 'bakery':
            bread += 3
        elif kind == 'nest':
            bread -= 1

    # Clamp to non-negative
    if bread < 0:
        bread = 0

    state['bread'] = bread
    return state


def add_building(state: State, kind: str, x: int, y: int, n: int) -> State:
    """Attempt to add a building of the given kind at (x, y) on an n-by-n grid."""
    # Validate bounds
    if not (0 <= x < n and 0 <= y < n):
        return state

    buildings: List[Building] = state.get('buildings', [])

    # Check for occupancy
    for b in buildings:
        if b.get('x') == x and b.get('y') == y:
            return state

    # Add new building
    new_building: Building = {'kind': kind, 'x': x, 'y': y}
    buildings.append(new_building)
    state['buildings'] = buildings
    return state
