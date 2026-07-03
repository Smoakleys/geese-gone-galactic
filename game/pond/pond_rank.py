# BUILT BY ICARUS (gpt-oss:20b) for OP-16 (pond rank/progression) via the full gate. tests/test_pond_rank.py
def pond_rank(score):
    """
    Return the pond rank as a string based on the score.
    
    - 'hamlet' if score < 20
    - 'village' if 20 <= score < 50
    - 'town' if 50 <= score < 100
    - 'city' if score >= 100
    
    Parameters:
        score (int or float): The score to evaluate.
    
    Returns:
        str: The rank name.
    """
    if score < 20:
        return "hamlet"
    elif score < 50:
        return "village"
    elif score < 100:
        return "town"
    else:
        return "city"