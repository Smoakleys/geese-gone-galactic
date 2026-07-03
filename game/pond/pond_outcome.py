# BUILT BY ICARUS (gpt-oss:20b) for OP-10 (pond outcome) via the full gate. tests/test_pond_outcome.py
def pond_outcome(state, reach):
    """
    Evaluate the pond outcome based on bread and nest-fence proximity.

    Parameters:
        state (dict): Contains 'bread' (int) and 'buildings' (list of dicts).
                      Each building dict has keys 'kind', 'x', 'y'.
        reach (int): Manhattan distance threshold for safety.

    Returns:
        str: One of 'lost', 'unsafe', or 'thriving'.
    """
    bread = state.get('bread', 0)
    if bread <= 0:
        return 'lost'

    buildings = state.get('buildings', [])
    nests = [b for b in buildings if b.get('kind') == 'nest']
    fences = [b for b in buildings if b.get('kind') == 'fence']

    # No nests means safe by default
    if not nests:
        return 'thriving'

    for nest in nests:
        nx, ny = nest['x'], nest['y']
        # Check if any fence is within Manhattan distance `reach`
        if not any(abs(nx - fx) + abs(ny - fy) <= reach for fx, fy in [(f['x'], f['y']) for f in fences]):
            return 'unsafe'

    return 'thriving'