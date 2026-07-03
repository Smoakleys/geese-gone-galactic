# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-5 through the full pipeline
# (authored ticket -> agent -> python_syntax gate -> gatekeeper commit). Preserved as produced;
# behaviour locked by tests/test_predator.py. The One Pond predator-safety rule.


def is_safe(nests, fences, reach):
    """
    Return True if every nest is within Manhattan distance `reach`
    of at least one fence. An empty list of nests is considered safe.

    Parameters:
        nests (list[tuple[int,int]]): List of (x,y) coordinates for nests.
        fences (list[tuple[int,int]]): List of (x,y) coordinates for fences.
        reach (int): Maximum Manhattan distance allowed between a nest and a fence.

    Returns:
        bool: True if all nests are within reach of at least one fence, False otherwise.
    """
    # An empty list of nests is safe by definition
    if not nests:
        return True

    # If there are no fences but nests exist, they cannot be within reach
    if not fences:
        return False

    for nx, ny in nests:
        # Check if any fence satisfies the Manhattan distance condition
        if not any(abs(nx - fx) + abs(ny - fy) <= reach for fx, fy in fences):
            return False  # This nest is too far from all fences

    return True
