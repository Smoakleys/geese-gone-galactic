# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-2 through the full pipeline
# (authored ticket -> agent -> python_syntax gate -> gatekeeper commit, autonomy 1.0). Preserved as the
# agent produced it; behaviour locked by tests/test_pond_core.py. The game's first real logic module.
def tick(state):
    """Advance the pond bread economy by one tick.

    Adds one bakery bread and subtracts one goose bread from the state.
    The state is expected to be a dictionary with keys 'bakery_bread'
    and 'goose_bread'. Missing keys default to 0. Goose bread will not
    go below zero.

    Args:
        state (dict): Current state of the economy.

    Returns:
        dict: New state after the tick.
    """
    # Ensure we don't modify the original state in place
    new_state = dict(state)

    # Add bakery bread
    new_state['bakery_bread'] = new_state.get('bakery_bread', 0) + 1

    # Subtract goose bread, but not below zero
    current_goose = new_state.get('goose_bread', 0)
    new_state['goose_bread'] = max(current_goose - 1, 0)

    return new_state
