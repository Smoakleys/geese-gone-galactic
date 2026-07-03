"""Self-distillation data pipeline (PLAN Part 5, Levers 3 & 5).

Turn gate-passing (ticket -> committed module) pairs into supervised fine-tuning (SFT) records, so
Icarus's own verified successes become free QLoRA training data. This is the plan's real lever for raising
*unaided* capability beyond the base model's ceiling: train the local model on instruction->solution pairs
that ALREADY cleared the strict gate (behavioural check + reviewer), never on unverified output.

This module only PREPARES the data (stdlib-only, offline). The actual QLoRA run is an external GPU step
(out of scope here); the JSONL it writes is the standard `{"instruction", "input", "output"}` shape most
QLoRA trainers accept. A future extension can capture full agent *trajectories* (plan->act->observe) rather
than just final solutions; the (task -> solution) pairs here are the minimal useful foundation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def _instruction(ticket) -> str:
    """The FULL task spec as the SFT instruction: title + acceptance criteria + behavioural contracts.

    Training on the whole requirement (not just the title) teaches the model the exact-output contracts it
    must satisfy, which is what the gate actually enforces.
    """
    parts = [ticket.title.strip()]
    for c in getattr(ticket, "acceptance_criteria", []) or []:
        parts.append(f"- {c.text}")
    for ex in getattr(ticket, "behavior", []) or []:
        parts.append(f"- must satisfy: {ex['call']} == {ex['expect']!r}")
    return "\n".join(parts)


def is_trivial_hardcode(output: str) -> bool:
    """True if the solution just prints a bare literal (``print(715)``, ``print('abc')``) with no
    computation. These pass the instance checker but are POISON as training data: a coding model learns
    to guess/hardcode the answer instead of writing general code. Exclude them from the SFT corpus."""
    import ast
    body = output.strip()
    if "\n" in body or not (body.startswith("print(") and body.endswith(")")):
        return False
    try:
        node = ast.parse(body[6:-1], mode="eval").body
    except Exception:
        return False
    return isinstance(node, ast.Constant)   # a bare constant, no expression/vars/calls


def _strip_provenance(src: str) -> str:
    """Drop the leading ``# BUILT BY ICARUS ...`` provenance header so the training OUTPUT is the actual
    code. Otherwise a fine-tune learns to reproduce that meta-comment (autonomy/gate/ticket chatter) at the
    top of every solution — pure noise. Only strips the leading contiguous comment block, and only when it
    starts with the provenance marker, so a module's own real leading comments are left intact."""
    lines = src.splitlines()
    if not lines or not lines[0].lstrip().startswith("# BUILT BY ICARUS"):
        return src
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("#"):
        i += 1
    while i < len(lines) and not lines[i].strip():   # drop one blank separator after the header
        i += 1
    body = "\n".join(lines[i:])
    return body + "\n" if src.endswith("\n") and not body.endswith("\n") else body


def build_sft_records(tickets: Iterable, module_dir: Path) -> "list[dict]":
    """One SFT record per gate-passing (ticket, committed module) pair.

    A ticket's `behavior` examples name the module(s) it produced; if that module exists in `module_dir`
    (i.e. it was verified + committed), emit `{instruction: full-spec, input: "", output: source}`.
    Skips tickets whose module isn't present (not yet built) so the set is exactly the verified successes.
    """
    module_dir = Path(module_dir)
    records: "list[dict]" = []
    seen: "set[str]" = set()
    for t in tickets:
        for ex in getattr(t, "behavior", []) or []:
            name = ex.get("module")
            if not name or name in seen:
                continue
            src = module_dir / name
            if src.exists():
                seen.add(name)
                records.append({
                    "instruction": _instruction(t),
                    "input": "",
                    "output": _strip_provenance(src.read_text(encoding="utf-8")),
                    "meta": {"ticket": t.id, "module": name, "gate": "python_behavior+reviewer"},
                })
    return records


def write_jsonl(records: "Iterable[dict]", path: Path) -> int:
    """Write records as one JSON object per line (QLoRA-ready). Returns the count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n
