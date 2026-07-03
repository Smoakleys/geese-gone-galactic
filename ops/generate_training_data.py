"""Scale the self-distillation dataset via the PROCEDURAL generators (PLAN Lever 1 + 3).

Hand-authored tickets don't reach QLoRA scale. The `gen_*` generators produce infinite non-repeating
instances, each with its own deterministic checker; this runs each through the agent loop and keeps ONLY
the checker-passing solutions as SFT records `{instruction: prompt, output: solution}`. The gate filters,
so the data is verified by construction and non-memorisable (fresh seeds).

This is a LONG GPU job at scale (each instance runs the local agent). Usage:
    python ops/generate_training_data.py --n 200 --seed 1000 --out data/generated_sft.jsonl
Smoke-run it small first. Then merge into the QLoRA data (see docs/DISTILL.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.icarus.distill import is_trivial_hardcode, write_jsonl  # noqa: E402
from harness.icarus.eval.capability import (  # noqa: E402
    gen_sum, gen_reverse, gen_json, gen_fizzbuzz, gen_fix_bug, gen_fix_range_bug, gen_read_sum,
    gen_read_max, gen_read_evens, gen_read_sorted, gen_grep_count, gen_find_secret, gen_economy, gen_placement, gen_pond_tick,
    gen_water_access, gen_predator_safety, gen_granary, gen_pond_score, gen_pond_outcome,
)

# logic/coding generators only (scene/render need Godot + the 30B; keep this data pure-logic).
# The gen_read_* family reads a per-instance input file -> non-hardcodable -> forces REAL general code
# (unlike arithmetic-in-the-prompt tasks the agent can shortcut to print(<literal>); see is_trivial_hardcode).
LOGIC_GENERATORS = [
    gen_sum, gen_reverse, gen_json, gen_fizzbuzz, gen_fix_bug, gen_fix_range_bug, gen_read_sum,
    gen_read_max, gen_read_evens, gen_read_sorted, gen_grep_count, gen_find_secret, gen_economy, gen_placement, gen_pond_tick,
    gen_water_access, gen_predator_safety, gen_granary, gen_pond_score, gen_pond_outcome,
]


def _solution_source(ws: Path) -> "str | None":
    """The Python file the agent produced in the workspace (the solution)."""
    pys = [p for p in ws.rglob("*.py") if p.is_file() and p.stat().st_size > 0]
    if not pys:
        return None
    return max(pys, key=lambda p: p.stat().st_size).read_text(encoding="utf-8", errors="replace")


def generate(model, n: int, seed: int, out: Path, *, run_timeout: float = 30.0) -> int:
    """Run `n` generated instances through the agent; keep checker-passing solutions as SFT records."""
    from harness.icarus.eval.capability import run_battery
    import tempfile

    rng = Random(seed)
    records: "list[dict]" = []
    for i in range(n):
        gen = LOGIC_GENERATORS[i % len(LOGIC_GENERATORS)]
        inst = gen(Random(seed + i))
        ws_root = Path(tempfile.mkdtemp(prefix="gendata_"))
        rep = run_battery(model, [inst], ws_root, max_steps=10, run_timeout=run_timeout, use_notebook=False)
        if rep.results and rep.results[0].passed:
            src = _solution_source(ws_root / inst.id)
            # Keep only REAL code: a checker-passing `print(<literal>)` hardcodes the answer and would
            # teach a fine-tune to guess instead of compute -- poison as SFT data (see distill).
            if src and not is_trivial_hardcode(src):
                records.append({"instruction": inst.prompt.strip(), "input": "", "output": src,
                                "meta": {"generator": gen.__name__, "id": inst.id, "gate": "checker"}})
    return write_jsonl(records, out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", default="data/generated_sft.jsonl")
    ap.add_argument("--model", default="gpt-oss:20b")
    args = ap.parse_args()
    from harness.icarus.agent.ollama import OllamaAgentModel
    model = OllamaAgentModel(args.model, temperature=0.2)
    n = generate(model, args.n, args.seed, Path(args.out))
    print(f"kept {n} checker-passing solutions -> {args.out}")


if __name__ == "__main__":
    main()
