# BUILT BY ICARUS (gpt-oss:20b) for OP-6 (revised: +well colour) via the full gate. tests/test_pond_scene.py
def build_body(buildings):
    """
    Generate GDScript statements to add boxes for each building.
    
    Parameters:
        buildings (list of dict): Each dict must contain 'kind', 'x', and 'y' keys.
        
    Returns:
        str: Newline-separated GDScript lines, one per building.
    """
    color_map = {
        'bakery':  'Color(0.5, 0.3, 0.1)',
        'nest':    'Color(0.8, 0.7, 0.4)',
        'fence':   'Color(0.5, 0.5, 0.5)',
        'granary': 'Color(0.7, 0.5, 0.2)',
        'well':    'Color(0.2, 0.4, 0.8)'
    }
    
    lines = []
    for b in buildings:
        kind = b.get('kind', '')
        x = b.get('x', 0)
        y = b.get('y', 0)
        color = color_map.get(kind, 'Color.WHITE')
        line = f"add_box(root, Vector3(1, 1, 1), {color}, Vector3({x} * 2, 0.5, {y} * 2))"
        lines.append(line)
    
    return '\n'.join(lines)