# BUILT BY ICARUS (gpt-oss:20b) for OP-11 (water access) via the full gate. tests/test_water_access.py
def has_water(buildings, reach):
    """
    Return True iff every bakery is within Manhattan distance <= reach of at least one well.
    If there are no bakeries, return True.

    Parameters:
        buildings (list[dict]): Each dict must have keys 'kind', 'x', 'y'.
        reach (int or float): Maximum allowed Manhattan distance from a bakery to a well.

    Returns:
        bool: True if all bakeries are reachable by at least one well within the given reach.
    """
    # Extract positions of wells
    wells = [(b['x'], b['y']) for b in buildings if b.get('kind') == 'well']

    # If no bakeries, condition is vacuously satisfied
    bakery_positions = [(b['x'], b['y']) for b in buildings if b.get('kind') == 'bakery']
    if not bakery_positions:
        return True

    # For each bakery, check if any well is within reach
    for bx, by in bakery_positions:
        reachable = False
        for wx, wy in wells:
            if abs(bx - wx) + abs(by - wy) <= reach:
                reachable = True
                break
        if not reachable:
            return False

    return True