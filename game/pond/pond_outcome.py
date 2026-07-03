# BUILT BY ICARUS (gpt-oss:20b) for OP-10 (revised: +dry/water) via the full gate. tests/test_pond_outcome.py
def pond_outcome(state, reach):
    """
    Evaluate the state of the pond.

    Parameters
    ----------
    state : dict
        Dictionary containing 'bread' (int) and a list of building dictionaries.
        Each building dictionary has keys 'kind', 'x', and 'y'.
    reach : int
        Manhattan distance threshold for water and safety checks.

    Returns
    -------
    str
        One of 'lost', 'dry', 'unsafe', or 'thriving' according to the rules:
        1. If bread <= 0 -> 'lost'
        2. If any bakery is not within reach of a well -> 'dry'
           (no bakeries => considered watered)
        3. If any nest is not within reach of a fence -> 'unsafe'
           (no nests => considered safe)
        4. Otherwise -> 'thriving'
    """
    # Rule 1: Bread check
    if state.get('bread', 0) <= 0:
        return 'lost'

    buildings = state.get('buildings', [])

    # Separate buildings by kind for quick lookup
    wells = [(b['x'], b['y']) for b in buildings if b['kind'] == 'well']
    fences = [(b['x'], b['y']) for b in buildings if b['kind'] == 'fence']

    # Helper to compute Manhattan distance
    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # Rule 2: Water access for bakeries
    bakeries = [(b['x'], b['y']) for b in buildings if b['kind'] == 'bakery']
    if bakeries:
        for bx, by in bakeries:
            # Check if any well is within reach
            if not any(manhattan((bx, by), w) <= reach for w in wells):
                return 'dry'

    # Rule 3: Predator safety for nests
    nests = [(b['x'], b['y']) for b in buildings if b['kind'] == 'nest']
    if nests:
        for nx, ny in nests:
            # Check if any fence is within reach
            if not any(manhattan((nx, ny), f) <= reach for f in fences):
                return 'unsafe'

    # Rule 4: All checks passed
    return 'thriving'