# BUILT BY ICARUS (gpt-oss:20b) for OP-17 (goose population) via the full gate. tests/test_goose_count.py
def goose_count(buildings):
    """
    Count the number of geese in a list of building dictionaries.
    
    Each building is expected to be a dict with at least a 'kind' key.
    A building of kind 'nest' houses 4 geese; all other kinds house none.
    
    Parameters
    ----------
    buildings : Iterable[dict]
        An iterable of building dictionaries.

    Returns
    -------
    int
        Total number of geese across all buildings.
    """
    return sum(4 for b in buildings if b.get('kind') == 'nest')