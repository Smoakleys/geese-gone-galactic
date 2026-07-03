# BUILT BY ICARUS (gpt-oss:20b) for OP-12 (pond score) via the full gate. tests/test_pond_score.py
def pond_score(state):
    """
    Calculate the net-worth score for a pond based on its state.

    Parameters
    ----------
    state : dict
        A dictionary containing at least two keys:
            - 'bread' (int): The base bread value.
            - 'buildings' (list of dict): Each building dict must contain a 'kind' key.

    Returns
    -------
    int
        The total score: bread plus weighted values for each building kind.
    """
    # Base bread value; default to 0 if missing or not an int
    try:
        base = int(state.get('bread', 0))
    except (TypeError, ValueError):
        base = 0

    # Weight mapping for building kinds
    weights = {
        'bakery': 10,
        'granary': 5,
        'nest': 3
    }

    total_building_score = 0
    buildings = state.get('buildings', [])
    if isinstance(buildings, list):
        for b in buildings:
            kind = b.get('kind')
            # Use default weight of 2 for unknown kinds or missing kind
            weight = weights.get(kind, 2)
            total_building_score += weight

    return base + total_building_score