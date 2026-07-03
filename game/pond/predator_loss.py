# BUILT BY ICARUS (gpt-oss:20b) for OP-14 (predator loss) via the full gate. tests/test_predator_loss.py
def predator_loss(state, reach):
    """
    Calculate the total bread eaten by predators this tick.

    Parameters
    ----------
    state : dict
        Dictionary containing a key 'buildings' which is a list of building dictionaries.
        Each building dictionary must have keys 'kind', 'x', and 'y'.
    reach : int
        Manhattan distance within which a fence protects a nest.

    Returns
    -------
    int
        Total amount of bread eaten by predators (2 per unguarded nest).
    """
    buildings = state.get('buildings', [])
    # Collect positions of all fences for quick lookup
    fences = [(b['x'], b['y']) for b in buildings if b.get('kind') == 'fence']

    total_bread_eaten = 0

    for building in buildings:
        if building.get('kind') != 'nest':
            continue

        nest_x, nest_y = building.get('x'), building.get('y')
        guarded = False

        # Check if any fence is within the specified Manhattan distance
        for fx, fy in fences:
            if abs(nest_x - fx) + abs(nest_y - fy) <= reach:
                guarded = True
                break

        if not guarded:
            total_bread_eaten += 2

    return total_bread_eaten