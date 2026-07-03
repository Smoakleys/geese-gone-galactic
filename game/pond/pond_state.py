# BUILT BY ICARUS (gpt-oss:20b) for OP-4 (revised: granary synergy in step) via the full gate. tests/test_pond_state.py
"""
One Pond simulation module.

Functions:
- step(state): returns the next state after one tick.
- add_building(state, kind, x, y, n): adds a building if placement is valid.
"""

from copy import deepcopy

def step(state):
    """
    Advance the simulation by one tick.

    Parameters
    ----------
    state : dict
        Must contain 'bread' (int) and 'buildings' (list of dicts with keys:
        'kind', 'x', 'y').

    Returns
    -------
    dict
        New state dictionary with updated bread count.
    """
    # Ensure required keys exist
    bread = int(state.get('bread', 0))
    buildings = deepcopy(state.get('buildings', []))

    # Count building types
    num_granaries = sum(1 for b in buildings if b['kind'] == 'granary')
    num_bakeries   = sum(1 for b in buildings if b['kind'] == 'bakery')
    num_nests      = sum(1 for b in buildings if b['kind'] == 'nest')

    # Bread production and consumption
    delta = num_bakeries * (3 + num_granaries)
    new_bread = max(bread + delta - num_nests, 0)

    return {
        'bread': new_bread,
        'buildings': buildings
    }

def add_building(state, kind, x, y, n):
    """
    Add a building to the state if placement is valid.

    Parameters
    ----------
    state : dict
        Current simulation state.
    kind : str
        Building type (e.g., 'bakery', 'granary', 'nest').
    x, y : int
        Coordinates on an n-by-n grid.
    n : int
        Grid size; coordinates must satisfy 0 <= x < n and 0 <= y < n.

    Returns
    -------
    dict
        New state with the building added if placement is valid;
        otherwise returns the original state unchanged.
    """
    # Validate bounds
    if not (0 <= x < n and 0 <= y < n):
        return deepcopy(state)

    buildings = deepcopy(state.get('buildings', []))

    # Check for existing building at same location
    for b in buildings:
        if b['x'] == x and b['y'] == y:
            return deepcopy(state)  # placement invalid

    # Add new building
    new_building = {'kind': kind, 'x': x, 'y': y}
    buildings.append(new_building)

    return {
        'bread': int(state.get('bread', 0)),
        'buildings': buildings
    }