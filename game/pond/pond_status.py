# BUILT BY ICARUS (gpt-oss:20b) for OP-9 (pond status: predator safety + state) via the full gate.
# Preserved as produced; behaviour locked by tests/test_pond_status.py.
def pond_status(state, reach):
    """
    Summarise a pond.
    
    Parameters
    ----------
    state : dict
        Expected to contain 'bread' (int) and 'buildings' (list of dicts).
        Each building dict must have keys 'kind', 'x', 'y'.
    reach : int
        Manhattan distance threshold for safety check.
    
    Returns
    -------
    dict
        {'bread': <int>, 'safe': <bool>}
    """
    bread = state.get('bread', 0)
    buildings = state.get('buildings', [])
    
    # Separate nests and fences with their coordinates
    nests = [(b['x'], b['y']) for b in buildings if b.get('kind') == 'nest']
    fences = [(b['x'], b['y']) for b in buildings if b.get('kind') == 'fence']
    
    # If there are no nests, the pond is safe by definition
    if not nests:
        return {'bread': bread, 'safe': True}
    
    # For each nest, check if at least one fence is within reach
    for nx, ny in nests:
        if not any(abs(nx - fx) + abs(ny - fy) <= reach for fx, fy in fences):
            return {'bread': bread, 'safe': False}
    
    return {'bread': bread, 'safe': True}