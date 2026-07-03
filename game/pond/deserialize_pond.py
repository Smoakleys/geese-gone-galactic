# BUILT BY ICARUS (gpt-oss:20b) for OP-31 (pond deserialization) via the full gate. tests/test_deserialize_pond.py
"""
deserialize_pond.py

Provides a single function `deserialize_pond(text)` that parses a pond description string
into a state dictionary.

The format is:

    bread={N}[;{kind}@{x},{y}...]

- The first part must start with "bread=" followed by an integer.
- Zero or more building parts may follow, separated by semicolons.
  Each building part has the form "{kind}@{x},{y}" where kind is a string
  and x,y are integers.

The function returns:

    {
        'bread': int,
        'buildings': [
            {'kind': str, 'x': int, 'y': int},
            ...
        ]
    }

The order of buildings in the returned list matches the order in the input string.
"""

def deserialize_pond(text: str) -> dict:
    """
    Parse a pond description string into a state dictionary.

    Parameters
    ----------
    text : str
        Pond description, e.g. "bread=3;house@1,2;tree@-4,7".

    Returns
    -------
    dict
        Dictionary with keys 'bread' (int) and 'buildings' (list of dicts).
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    parts = text.split(';')
    if not parts:
        raise ValueError("Empty input string")

    # Parse bread
    bread_part = parts[0].strip()
    if not bread_part.startswith('bread='):
        raise ValueError(f"Expected 'bread=' prefix, got: {bread_part!r}")
    try:
        bread_value = int(bread_part[len('bread='):])
    except ValueError as exc:
        raise ValueError(f"Invalid bread value in: {bread_part}") from exc

    buildings = []
    for part in parts[1:]:
        if not part.strip():
            continue  # skip empty segments
        try:
            kind, coord_str = part.split('@', 1)
            x_str, y_str = coord_str.split(',', 1)
            building = {
                'kind': kind,
                'x': int(x_str),
                'y': int(y_str)
            }
            buildings.append(building)
        except Exception as exc:
            raise ValueError(f"Invalid building part: {part!r}") from exc

    return {'bread': bread_value, 'buildings': buildings}