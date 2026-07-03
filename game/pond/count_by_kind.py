# BUILT BY ICARUS (gpt-oss:20b) for OP-20 (building inventory) via the full gate. tests/test_count_by_kind.py
def count_by_kind(buildings):
    """
    Count occurrences of each 'kind' in a list of building dictionaries.

    Parameters:
        buildings (list): A list where each element is a dict that may contain a 'kind' key.

    Returns:
        dict: Mapping from kind to the number of times it appears.
              Kinds with zero count are omitted. An empty input returns {}.
    """
    result = {}
    for building in buildings:
        # Safely get the kind; skip if missing or None
        kind = building.get('kind')
        if kind is None:
            continue
        result[kind] = result.get(kind, 0) + 1
    return result