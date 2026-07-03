# BUILT BY ICARUS (gpt-oss:20b) for OP-13 (pond advice/hints) via the full gate. tests/test_pond_advice.py
def pond_advice(state, reach):
    """
    Inspect the state['buildings'] list and return a short advice string.
    
    Parameters
    ----------
    state : dict
        Expected to contain a key 'buildings' which is an iterable of dicts,
        each with keys 'kind', 'x', and 'y'.
    reach : int or float
        Manhattan distance threshold for proximity checks.
    
    Returns
    -------
    str
        One of:
            "build a bakery"
            "build a well"
            "build a fence"
            "looking good"
    """
    buildings = state.get("buildings", [])
    
    # Separate buildings by kind
    bakeries = [(b["x"], b["y"]) for b in buildings if b.get("kind") == "bakery"]
    wells     = [(w["x"], w["y"]) for w in buildings if w.get("kind") == "well"]
    nests     = [(n["x"], n["y"]) for n in buildings if n.get("kind") == "nest"]
    fences    = [(f["x"], f["y"]) for f in buildings if f.get("kind") == "fence"]

    # 1. No bakery at all
    if not bakeries:
        return "build a bakery"

    # Helper to compute Manhattan distance
    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # 2. Any bakery not within reach of a well?
    if wells:  # there is at least one well
        for bx, by in bakeries:
            if all(manhattan((bx, by), (wx, wy)) > reach for wx, wy in wells):
                return "build a well"
    else:
        # No wells exist; any bakery automatically needs a well
        return "build a well"

    # 3. Any nest not within reach of a fence?
    if nests:  # there is at least one nest
        if not fences:
            # No fences exist, so nests need protection
            return "build a fence"
        for nx, ny in nests:
            if all(manhattan((nx, ny), (fx, fy)) > reach for fx, fy in fences):
                return "build a fence"

    # 4. All checks passed
    return "looking good"