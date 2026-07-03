# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-7 through the full pipeline WITH the
# real local Stage-B reviewer. Preserved as produced; behaviour locked by tests/test_granary.py.
def production(bakeries, granaries):
    """
    Calculate total bread produced per tick.

    Each bakery produces a base of 3 units.
    Every granary adds +1 to every bakery's output.
    Total = bakeries * (3 + granaries).

    If there are no bakeries, the result is always 0 regardless of granaries.
    """
    if bakeries == 0:
        return 0
    return bakeries * (3 + granaries)