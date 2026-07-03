# BUILT BY ICARUS (gpt-oss:20b) for OP-30 (pond serialization) via the full gate. tests/test_serialize_pond.py
def serialize_pond(state):
    bread = state.get('bread', 0)
    buildings = state.get('buildings', [])
    parts = [f"bread={bread}"]
    for b in buildings:
        kind = b.get('kind')
        x = b.get('x')
        y = b.get('y')
        parts.append(f"{kind}@{x},{y}")
    return ";".join(parts)