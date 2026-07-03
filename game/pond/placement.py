# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-3 through the full pipeline
# (authored ticket -> agent -> python_syntax gate -> gatekeeper commit, autonomy 1.0). Preserved as the
# agent produced it; behaviour locked by tests/test_pond_core.py.
"""
Utility module for validating building placements on a square pond grid.

The `is_valid` function checks that all provided cell coordinates are within the bounds of an n×n grid
and that no two cells overlap (i.e., duplicate coordinates).  It returns True if the placement is valid,
otherwise False.
"""

from __future__ import annotations


def is_valid(cells: "list[tuple[int, int] | list[int]]", n: int) -> bool:
    """
    Validate a building layout on an n×n grid.

    Parameters
    ----------
    cells : list of (x, y) tuples or lists
        The coordinates of the cells that the building occupies.
    n : int
        Size of the square grid (valid indices are 0 .. n-1).

    Returns
    -------
    bool
        True if all cells are within bounds and no duplicates exist; False otherwise.
    """
    seen = set()
    for cell in cells:
        # Ensure we have a tuple of two ints
        try:
            x, y = int(cell[0]), int(cell[1])
        except (TypeError, ValueError, IndexError):
            return False

        if not (0 <= x < n and 0 <= y < n):
            return False

        coord = (x, y)
        if coord in seen:
            return False
        seen.add(coord)

    return True
