# BUILT BY ICARUS (gpt-oss:20b) for OP-27 (affordable buildings) via the full gate. tests/test_affordable_buildings.py
def affordable_buildings(bread):
    """
    Return a sorted list of building kinds whose bread cost is <= `bread`.
    
    Costs:
        bakery 5
        granary 4
        well    3
        fence   2
        nest    1
    
    Parameters
    ----------
    bread : int or float
        The amount of bread available.
    
    Returns
    -------
    list[str]
        Alphabetically sorted building kinds affordable with the given bread.
    """
    costs = {
        "bakery": 5,
        "granary": 4,
        "well": 3,
        "fence": 2,
        "nest": 1,
    }
    # Filter buildings whose cost is <= bread
    affordable = [name for name, cost in costs.items() if cost <= bread]
    # Return alphabetically sorted list
    return sorted(affordable)