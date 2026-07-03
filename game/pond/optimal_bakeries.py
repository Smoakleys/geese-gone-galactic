# BUILT BY ICARUS (gpt-oss:20b) for OP-32 (production planning) via the full gate. tests/test_optimal_bakeries.py
def optimal_bakeries(target, granaries):
    """
    Return the minimum number of bakeries needed so that each bakery produces (3 + granaries) bread per tick,
    and the total production is at least `target`. If target <= 0, return 0.
    Uses integer arithmetic only.
    """
    if target <= 0:
        return 0
    denom = 3 + granaries
    # If a bakery produces zero or negative bread, we cannot reach a positive target.
    if denom <= 0:
        return 0
    return (target + denom - 1) // denom