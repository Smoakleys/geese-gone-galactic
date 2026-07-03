# BUILT BY ICARUS (local agent, gpt-oss:20b) for ticket OP-6 through the full pipeline WITH a real local
# Stage-B reviewer (LLMReviewer + OllamaChatClient) and a precise acceptance criterion. Preserved as
# produced; behaviour locked by tests/test_pond_scene.py. Bridges pond state -> renderable GDScript.
def build_body(buildings):
    """
    Generate GDScript statements to add boxes for each building.

    Parameters:
        buildings (list of dict): Each dict must contain 'kind', 'x', and 'y' keys.
            - kind (str): Type of the building ('bakery', 'nest', 'fence', or others).
            - x (int): X coordinate in grid units.
            - y (int): Y coordinate in grid units.

    Returns:
        str: Newline-separated GDScript statements, one per building.
    """
    lines = []
    for b in buildings:
        kind = b.get('kind', '')
        x = b.get('x', 0)
        y = b.get('y', 0)

        if kind == 'bakery':
            color = 'Color(0.5, 0.3, 0.1)'
        elif kind == 'nest':
            color = 'Color(0.8, 0.7, 0.4)'
        elif kind == 'fence':
            color = 'Color(0.5, 0.5, 0.5)'
        else:
            color = 'Color.WHITE'

        line = f'add_box(root, Vector3(1, 1, 1), {color}, Vector3({x} * 2, 0.5, {y} * 2))'
        lines.append(line)

    return '\n'.join(lines)