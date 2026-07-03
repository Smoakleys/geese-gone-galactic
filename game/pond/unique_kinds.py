# BUILT BY ICARUS (gpt-oss:20b) for OP-23 (distinct kinds) via the full gate. tests/test_unique_kinds.py
def unique_kinds(buildings):
    """Return a sorted list of distinct 'kind' values from buildings."""
    return sorted({b['kind'] for b in buildings})