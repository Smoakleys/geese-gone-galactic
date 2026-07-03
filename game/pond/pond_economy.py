# BUILT BY ICARUS (gpt-oss:20b) for OP-8 via the real-reviewer pipeline. behaviour: tests/test_pond_economy.py
def tick_bread(buildings):
    """
    Calculate the net bread change for one tick.

    Parameters:
        buildings (list): A list of dictionaries, each with a 'kind' key.
                          Valid kinds are 'bakery', 'granary', and 'nest'.

    Returns:
        int: Net bread change. Positive values indicate bread production,
             negative values indicate consumption.
    """
    bakeries = sum(1 for b in buildings if b.get('kind') == 'bakery')
    granaries = sum(1 for g in buildings if g.get('kind') == 'granary')
    nests = sum(1 for n in buildings if n.get('kind') == 'nest')

    return bakeries * (3 + granaries) - nests