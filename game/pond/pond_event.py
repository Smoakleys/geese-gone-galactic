# BUILT BY ICARUS (gpt-oss:20b) for OP-28 (pond events) via the full gate. tests/test_pond_event.py
def apply_event(state, event):
    """
    Return a new state dict after applying the named event to state['bread'].
    
    Parameters
    ----------
    state : dict
        Original state containing at least 'bread' and optionally other keys.
    event : str
        The name of the event: 'harvest', 'fox', or 'flood'.
        
    Returns
    -------
    dict
        A new dictionary with updated 'bread' value, unchanged 'buildings',
        and all other keys preserved. Bread is clamped to a minimum of 0.
    """
    # Create a shallow copy so the original state remains untouched
    new_state = state.copy()
    
    # Get current bread amount; default to 0 if missing
    bread = new_state.get('bread', 0)
    
    if event == 'harvest':
        bread += 10
    elif event == 'fox':
        bread -= 5
    elif event == 'flood':
        bread //= 2
    
    # Clamp to non-negative value
    if bread < 0:
        bread = 0
    
    new_state['bread'] = bread
    return new_state