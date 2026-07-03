# BUILT BY ICARUS (gpt-oss:20b) for OP-15 (build cost) via the full gate. tests/test_build_cost.py
def total_cost(buildings):
    """
    Calculate the total bread cost for a list of building dictionaries.

    Parameters
    ----------
    buildings : Iterable[dict]
        Each dictionary must contain a 'kind' key. The kind determines the cost:
            - 'bakery': 5
            - 'granary': 4
            - 'well': 3
            - 'fence': 2
            - 'nest': 1
        Any unknown kind contributes 0 to the total.

    Returns
    -------
    int
        The sum of costs for all buildings.
    """
    cost_map = {
        "bakery": 5,
        "granary": 4,
        "well": 3,
        "fence": 2,
        "nest": 1,
    }
    total = 0
    for building in buildings:
        kind = building.get("kind")
        total += cost_map.get(kind, 0)
    return total