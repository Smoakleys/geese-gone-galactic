"""Procedural capability battery + scorer for Icarus.

Each generator emits a fresh, randomized :class:`TaskInstance` with its OWN deterministic verifier —
so instances are infinite and non-memorizable (the anti-gaming lesson from Reasoning Gym), and a pass
means the produced code actually does the thing (verified by running it), not that it looked right.

``run_battery`` drives the agent loop on each instance and reports the pass rate. Run with
``use_notebook=False`` for the north-star UNAIDED score; the gap to the assisted score is the
dependence-gap metric.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Callable, Optional

from harness.icarus.agent import AgentModel, Notebook, run_agent

VerifyFn = Callable[[Path], "tuple[bool, str]"]


@dataclass
class TaskInstance:
    id: str
    category: str
    prompt: str
    verify: VerifyFn


@dataclass
class TaskResult:
    id: str
    category: str
    passed: bool
    steps: int
    finished: bool
    detail: str


@dataclass
class ScoreReport:
    results: list[TaskResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (sum(r.passed for r in self.results) / len(self.results)) if self.results else 0.0

    def summary(self) -> str:
        n = len(self.results)
        p = sum(r.passed for r in self.results)
        lines = [f"unaided pass rate: {p}/{n} = {self.pass_rate:.2f}"]
        for r in self.results:
            lines.append(f"  [{'PASS' if r.passed else 'FAIL'}] {r.id} ({r.category}) - {r.detail[:80]}")
        return "\n".join(lines)


# ---------------------------------------------------------------- verifier helper

def _run_py(ws: Path, filename: str, timeout: float = 15.0) -> "tuple[int, str, str]":
    proc = subprocess.run(["python", filename], cwd=str(ws),
                          capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


# ---------------------------------------------------------------- procedural generators

def gen_sum(rng: Random) -> TaskInstance:
    a, b = rng.randint(10, 999), rng.randint(10, 999)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:  # missing file, timeout, ...
            return False, f"could not run solution.py: {e}"
        return out == str(a + b), f"expected {a + b}, got {out!r} (rc={rc}{'; ' + err[:80] if err else ''})"

    return TaskInstance(
        f"sum_{a}_{b}", "arithmetic",
        f"Write a file solution.py that prints exactly the sum of {a} and {b} (the integer, nothing "
        f"else). Then run it with `python solution.py` to verify before finishing.", verify)


def gen_reverse(rng: Random) -> TaskInstance:
    word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(5, 9)))

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == word[::-1], f"expected {word[::-1]!r}, got {out!r}"

    return TaskInstance(
        f"reverse_{word}", "strings",
        f"Write solution.py that prints the string '{word}' reversed (nothing else). Run it to verify "
        f"before finishing.", verify)


def gen_json(rng: Random) -> TaskInstance:
    x, y = rng.randint(1, 100), rng.randint(1, 100)

    def verify(ws: Path) -> "tuple[bool, str]":
        p = ws / "config.json"
        if not p.exists():
            return False, "config.json not found"
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            return False, f"config.json is not valid JSON: {e}"
        return d.get("x") == x and d.get("y") == y, f"expected x={x} y={y}, got {d!r}"

    return TaskInstance(
        f"json_{x}_{y}", "config",
        f"Write a file config.json containing a JSON object with exactly two integer keys: "
        f"x = {x} and y = {y}.", verify)


def gen_fizzbuzz(rng: Random) -> TaskInstance:
    n = rng.randint(5, 20)

    def expected() -> str:
        out = []
        for i in range(1, n + 1):
            out.append("FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0
                       else "Buzz" if i % 5 == 0 else str(i))
        return "\n".join(out)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        ok = out.strip() == expected()
        return ok, (f"fizzbuzz(1..{n}) correct" if ok else f"fizzbuzz(1..{n}) mismatch (rc={rc})")

    return TaskInstance(
        f"fizzbuzz_{n}", "logic",
        f"Write solution.py that prints FizzBuzz for the numbers 1 to {n} inclusive, one per line "
        f"(Fizz for multiples of 3, Buzz for multiples of 5, FizzBuzz for multiples of 15). Run it to "
        f"verify before finishing.", verify)


def default_generators() -> "list[Callable[[Random], TaskInstance]]":
    return [gen_sum, gen_reverse, gen_json, gen_fizzbuzz]


def sample_battery(seed: int = 0, per_generator: int = 1,
                   generators: "Optional[list[Callable[[Random], TaskInstance]]]" = None) -> "list[TaskInstance]":
    """A reproducible battery: `per_generator` fresh instances from each generator, seeded."""
    rng = Random(seed)
    gens = generators or default_generators()
    return [g(rng) for _ in range(per_generator) for g in gens]


# ---------------------------------------------------------------- the runner

def run_battery(model: AgentModel, instances: "list[TaskInstance]", workspace_root: Path, *,
                max_steps: int = 10, run_timeout: float = 20.0, use_notebook: bool = False,
                notebook: "Optional[Notebook]" = None, vision=None) -> ScoreReport:
    """Drive the agent loop on each instance, verify the workspace, and score. Default is UNAIDED
    (no notebook) — the north-star capability measure."""
    report = ScoreReport()
    root = Path(workspace_root)
    for inst in instances:
        ws = root / inst.id
        res = run_agent(model, inst.prompt, ws, max_steps=max_steps, run_timeout=run_timeout,
                        use_notebook=use_notebook, notebook=notebook, vision=vision)
        try:
            passed, detail = inst.verify(ws)
        except Exception as e:  # a broken verifier must not crash the battery
            passed, detail = False, f"verify raised {type(e).__name__}: {e}"
        report.results.append(TaskResult(inst.id, inst.category, passed, res.steps, res.finished, detail))
    return report
