# BUILT BY ICARUS (gpt-oss:20b) for OP-22 (bread simulation) via the full gate. tests/test_simulate_bread.py
def simulate_bread(start, bakeries, nests, ticks):
    """
    Simulate the bread economy over a number of ticks.

    Parameters
    ----------
    start : int
        Initial amount of bread.
    bakeries : int
        Number of bakeries. Each tick adds `bakeries * 3` bread.
    nests : int
        Number of nests. Each tick subtracts this many bread.
    ticks : int
        Number of simulation ticks.

    Returns
    -------
    int
        Final amount of bread after all ticks, never negative.
    """
    bread = start
    for _ in range(ticks):
        bread += bakeries * 3
        bread -= nests
        if bread < 0:
            bread = 0
    return int(bread)