# BUILT BY ICARUS (gpt-oss:20b) for OP-21 (sort by distance) via the full gate. tests/test_sorted_by_distance.py
def sorted_by_distance(cells, point):
    """
    Return a new list of cells sorted by ascending Manhattan distance to the given point.
    Ties preserve original relative order (stable sort).
    
    Parameters:
        cells (list[tuple[int,int]]): List of (x, y) tuples.
        point (tuple[int,int]): Reference point (x, y).
        
    Returns:
        list[tuple[int,int]]: Sorted list.
    """
    if not cells:
        return []
    px, py = point
    # Python's sorted is stable; ties keep original order
    return sorted(cells, key=lambda cell: abs(cell[0] - px) + abs(cell[1] - py))