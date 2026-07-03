# BUILT BY ICARUS (gpt-oss:20b) for OP-19 (nearest fence search) via the full gate. tests/test_nearest_fence.py
"""
nearest_fence.py

Provides a function to find the fence closest to a given nest using Manhattan distance.
"""

def nearest_fence(nest, fences):
    """
    Return the fence (x, y) tuple that has the smallest Manhattan distance to the given
    `nest` tuple. If multiple fences are tied for the minimum distance, return the one
    that appears earliest in the input list.  If `fences` is empty, return None.

    Parameters:
        nest (tuple[int, int]): The (x, y) coordinates of the nest.
        fences (list[tuple[int, int]]): A list of (x, y) fence coordinates.

    Returns:
        tuple[int, int] | None: The closest fence or None if no fences are provided.
    """
    if not fences:
        return None

    best_fence = None
    best_dist = None

    for fence in fences:
        dx = abs(fence[0] - nest[0])
        dy = abs(fence[1] - nest[1])
        dist = dx + dy

        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_fence = fence

    return best_fence