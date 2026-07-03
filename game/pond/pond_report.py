# BUILT BY ICARUS (gpt-oss:20b) for OP-18 (status report line) via the full gate. tests/test_pond_report.py
def report(bread: int, rank: str, safe: bool) -> str:
    status = 'safe' if safe else 'in danger'
    return f"Pond: {bread} bread, rank {rank}, {status}"