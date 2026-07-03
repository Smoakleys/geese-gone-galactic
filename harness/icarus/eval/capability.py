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
    setup: "Optional[Callable[[Path], None]]" = None  # seed the workspace before the agent runs


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


def gen_fix_bug(rng: Random) -> TaskInstance:
    a, b = rng.randint(10, 99), rng.randint(10, 99)

    def setup(ws: Path) -> None:
        # A script that is SUPPOSED to print the sum but subtracts (a real bug to find + fix).
        (ws / "solution.py").write_text(f"# prints the sum of two numbers\nprint({a} - {b})\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(a + b), f"expected sum {a + b}, got {out!r}"

    return TaskInstance(
        f"fixbug_{a}_{b}", "debugging",
        f"solution.py already exists but is BROKEN: it should print the sum of {a} and {b}, but it "
        f"prints the wrong value. Read it, fix the bug, and run it to verify it prints {a + b}.",
        verify, setup=setup)


def gen_read_sum(rng: Random) -> TaskInstance:
    nums = [rng.randint(1, 50) for _ in range(rng.randint(4, 7))]

    def setup(ws: Path) -> None:
        (ws / "numbers.txt").write_text("\n".join(str(n) for n in nums) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(sum(nums)), f"expected total {sum(nums)}, got {out!r}"

    return TaskInstance(
        f"readsum_{sum(nums)}_{len(nums)}", "multi-file",
        "The file numbers.txt contains one integer per line. Write solution.py that reads numbers.txt, "
        "sums the integers, and prints the total. Run it to verify.", verify, setup=setup)


def gen_find_secret(rng: Random) -> TaskInstance:
    token = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    n_noise = rng.randint(15, 30)
    secret_line = rng.randint(0, n_noise)

    def setup(ws: Path) -> None:
        lines = []
        for i in range(n_noise + 1):
            lines.append(f"SECRET={token}" if i == secret_line else f"noise line {i} = {rng.randint(0,9999)}")
        (ws / "data.txt").write_text("\n".join(lines) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        p = ws / "answer.txt"
        if not p.exists():
            return False, "answer.txt not found"
        return p.read_text().strip() == token, f"expected {token!r}, got {p.read_text().strip()!r}"

    return TaskInstance(
        f"secret_{token}", "search",
        "data.txt has many lines; exactly one has the form SECRET=<value>. Find that line, and write "
        "ONLY the <value> (the token after SECRET=) into a file named answer.txt.", verify, setup=setup)


def gen_placement(rng: Random) -> TaskInstance:
    """A real pond mechanic (Icarus's strength): validate building placement on the grid."""
    n = rng.randint(4, 8)
    positions: "list[tuple[int, int]]" = []
    while len(positions) < rng.randint(2, 4):
        p = (rng.randint(0, n - 1), rng.randint(0, n - 1))
        if p not in positions:
            positions.append(p)
    if rng.random() > 0.5:  # inject a violation -> INVALID
        positions.append(positions[0] if rng.random() > 0.5 else (n + 1, 0))

    def _valid(cells: "list[tuple[int, int]]") -> bool:
        seen = set()
        for x, y in cells:
            if not (0 <= x < n and 0 <= y < n) or (x, y) in seen:
                return False
            seen.add((x, y))
        return True

    expected = "VALID" if _valid(positions) else "INVALID"
    pos_str = "; ".join(f"({x},{y})" for x, y in positions)
    id_pos = "_".join(f"{x}x{y}" for x, y in positions)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "place.py")
        except Exception as e:
            return False, f"could not run place.py: {e}"
        return out.strip() == expected, f"expected {expected}, got {out.strip()!r}"

    return TaskInstance(
        f"place_n{n}_{id_pos}", "game-logic",
        f"A goose pond has an {n}x{n} grid (valid cells 0..{n - 1}). Buildings occupy these cells: "
        f"{pos_str}. Write place.py that prints ONLY 'VALID' if every building is in-bounds AND no two "
        f"share a cell, otherwise 'INVALID'. Run it to verify.", verify)


def gen_economy(rng: Random) -> TaskInstance:
    """The real game's LOGIC domain (Icarus's strength): a pond bread-economy simulation."""
    bakeries = rng.randint(1, 4)
    geese = rng.randint(1, 3)
    start = rng.randint(5, 20)
    ticks = rng.randint(3, 8)
    final = start + ticks * (bakeries * 3 - geese)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "economy.py")
        except Exception as e:
            return False, f"could not run economy.py: {e}"
        return out == str(final), f"expected final bread {final}, got {out!r}"

    return TaskInstance(
        f"economy_{bakeries}b_{geese}g_{ticks}t_{start}s", "game-logic",
        f"Write economy.py that simulates a goose-pond bread economy for {ticks} ticks, starting with "
        f"{start} bread. Each tick: {bakeries} bakeries EACH produce 3 bread, and {geese} geese EACH "
        f"eat 1 bread. After the {ticks} ticks, print ONLY the final bread total. Run it to verify.",
        verify)


def gen_gdscript(rng: Random) -> TaskInstance:
    """The real domain: write valid Godot 4 GDScript, self-verifiable via godot --check-only."""
    n = rng.randint(2, 4)

    def verify(ws: Path) -> "tuple[bool, str]":
        from game.godot.binary import godot_path
        gd = ws / "scene.gd"
        if not gd.exists():
            return False, "scene.gd not found"
        godot = godot_path()
        if godot is None:
            return False, "godot not installed (cannot verify)"
        try:
            proc = subprocess.run([godot, "--headless", "--check-only", "--script", "scene.gd"],
                                  cwd=str(ws), capture_output=True, text=True, timeout=60)
        except Exception as e:
            return False, f"godot check crashed: {e}"
        return proc.returncode == 0, ("parses clean" if proc.returncode == 0
                                      else f"parse error: {(proc.stderr or proc.stdout).strip()[-140:]}")

    from game.godot.binary import godot_path as _gp
    godot = _gp() or "godot"
    prompt = (
        f"Write a valid Godot 4 GDScript file named scene.gd. It must `extends Node3D` and, in its "
        f"_ready() function, add a Camera3D (set to orthogonal projection) and {n} MeshInstance3D nodes "
        f"(each given a BoxMesh) as children. It must PASS Godot's syntax check. You can verify it "
        f"yourself with the run tool:\n  {godot} --headless --check-only --script scene.gd\n"
        f"Read any parse error and fix it before finishing.")
    return TaskInstance(f"gdscript_{n}", "gdscript", prompt, verify)


def gen_render(rng: Random) -> TaskInstance:
    """The semantic bar: a GDScript scene that must actually RENDER non-blank (not just parse)."""
    from game.godot.binary import godot_path as _gp
    godot = _gp() or "godot"

    def verify(ws: Path) -> "tuple[bool, str]":
        from game.godot.capture import green_dominance, render_gdscript
        gd_file = ws / "scene.gd"
        if not gd_file.exists():
            return False, "scene.gd not found"
        out = ws / "_render.png"
        ok, detail = render_gdscript(gd_file, out)
        if not ok:
            return False, detail
        try:
            gd = green_dominance(out)
        except Exception as e:
            return False, f"could not read render: {e}"
        # A real green scene is green-dominant; a gray/empty background (camera saw nothing) scores ~0.
        return gd >= 15.0, f"green-dominance {gd:.1f} (>=15 = the green plane rendered; ~0 = empty/gray)"

    prompt = (
        "Write a Godot 4 GDScript file named scene.gd (extends Node3D). In _ready() add a Camera3D "
        "(current, orthogonal projection, positioned away from the origin and aimed at it) and a large "
        "MeshInstance3D ground plane (PlaneMesh) with a bright green UNSHADED StandardMaterial3D. It must "
        "render non-blank. Use the render tool (path=scene.gd, out=p.png); the result reports the pixel "
        "variance - if it says BLANK, fix the scene (camera current? aimed at the plane?) and render "
        f"again. Syntax check: {godot} --headless --check-only --script scene.gd")
    return TaskInstance(f"render_scene_{rng.randint(1000, 9999)}", "render", prompt, verify)


def default_generators() -> "list[Callable[[Random], TaskInstance]]":
    return [gen_sum, gen_reverse, gen_json, gen_fizzbuzz,
            gen_fix_bug, gen_read_sum, gen_find_secret, gen_economy, gen_placement,
            gen_gdscript, gen_render]


def sample_battery(seed: int = 0, per_generator: int = 1,
                   generators: "Optional[list[Callable[[Random], TaskInstance]]]" = None) -> "list[TaskInstance]":
    """A reproducible battery: `per_generator` fresh instances from each generator, seeded."""
    rng = Random(seed)
    gens = generators or default_generators()
    return [g(rng) for _ in range(per_generator) for g in gens]


# ---------------------------------------------------------------- the runner

def run_battery(model: AgentModel, instances: "list[TaskInstance]", workspace_root: Path, *,
                max_steps: int = 10, run_timeout: float = 20.0, use_notebook: bool = False,
                notebook: "Optional[Notebook]" = None, vision=None, render_fn=None) -> ScoreReport:
    """Drive the agent loop on each instance, verify the workspace, and score. Default is UNAIDED
    (no notebook) — the north-star capability measure."""
    report = ScoreReport()
    root = Path(workspace_root)
    for inst in instances:
        ws = root / inst.id
        ws.mkdir(parents=True, exist_ok=True)
        if inst.setup is not None:
            inst.setup(ws)  # seed a broken file / data file the task refers to
        try:
            res = run_agent(model, inst.prompt, ws, max_steps=max_steps, run_timeout=run_timeout,
                            use_notebook=use_notebook, notebook=notebook, vision=vision,
                            render_fn=render_fn)
        except Exception as e:  # one task crashing must not kill the whole battery
            report.results.append(TaskResult(inst.id, inst.category, False, 0, False,
                                             f"agent crashed: {type(e).__name__}: {e}"))
            continue
        try:
            passed, detail = inst.verify(ws)
        except Exception as e:  # a broken verifier must not crash the battery
            passed, detail = False, f"verify raised {type(e).__name__}: {e}"
        report.results.append(TaskResult(inst.id, inst.category, passed, res.steps, res.finished, detail))
    return report
