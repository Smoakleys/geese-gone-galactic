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


def gen_fib(rng: Random) -> TaskInstance:
    n = rng.randint(10, 25)
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    want = a                                            # the nth Fibonacci number, fib(0)=0, fib(1)=1

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(want), f"expected fib({n})={want}, got {out!r} (rc={rc}{'; ' + err[:80] if err else ''})"

    return TaskInstance(
        f"fib_{n}", "algorithm",
        f"Write solution.py that prints exactly the {n}th Fibonacci number, where fib(0)=0, fib(1)=1, "
        f"fib(2)=1, fib(3)=2, and so on (print only the integer, nothing else). Run it with "
        f"`python solution.py` to verify before finishing.", verify)


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


def gen_fix_range_bug(rng: Random) -> TaskInstance:
    """A DIFFERENT debugging task (off-by-one, not a wrong operator) — to test if the weakness is
    general debugging or one bug-type."""
    n = rng.randint(6, 15)
    expected = n * (n + 1) // 2

    def setup(ws: Path) -> None:
        # should sum 1..n INCLUSIVE, but range(1, n) drops the last term (off-by-one).
        (ws / "solution.py").write_text(
            f"# should print the sum of 1..{n} inclusive\n"
            f"total = 0\nfor i in range(1, {n}):\n    total += i\nprint(total)\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(expected), f"expected {expected}, got {out!r}"

    return TaskInstance(
        f"fixrange_{n}", "debugging",
        f"solution.py should print the sum of 1..{n} inclusive (which is {expected}) but has an "
        f"off-by-one bug and prints the wrong value. Read it, fix the bug, and run it to verify it "
        f"prints {expected}.", verify, setup=setup)


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


def gen_read_max(rng: Random) -> TaskInstance:
    # input-reading (non-hardcodable): the numbers vary per instance, so the solution MUST read + compute.
    nums = [rng.randint(-40, 60) for _ in range(rng.randint(4, 8))]

    def setup(ws: Path) -> None:
        (ws / "numbers.txt").write_text("\n".join(str(n) for n in nums) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(max(nums)), f"expected max {max(nums)}, got {out!r}"

    return TaskInstance(
        f"readmax_{max(nums)}_{len(nums)}", "multi-file",
        "The file numbers.txt has one integer per line (some may be negative). Write solution.py that reads "
        "numbers.txt and prints the LARGEST integer. Run it to verify.", verify, setup=setup)


def gen_read_evens(rng: Random) -> TaskInstance:
    nums = [rng.randint(1, 99) for _ in range(rng.randint(5, 9))]
    evens = sum(1 for n in nums if n % 2 == 0)

    def setup(ws: Path) -> None:
        (ws / "numbers.txt").write_text("\n".join(str(n) for n in nums) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(evens), f"expected {evens} evens, got {out!r}"

    return TaskInstance(
        f"readevens_{evens}_{len(nums)}", "multi-file",
        "The file numbers.txt has one integer per line. Write solution.py that reads numbers.txt and prints "
        "HOW MANY of the integers are even. Run it to verify.", verify, setup=setup)


def gen_read_sorted(rng: Random) -> TaskInstance:
    # non-hardcodable + a LIST output (sorting + exact formatting), unlike the scalar-answer read tasks.
    nums = [rng.randint(1, 99) for _ in range(rng.randint(4, 7))]
    answer = " ".join(str(n) for n in sorted(nums))

    def setup(ws: Path) -> None:
        (ws / "numbers.txt").write_text("\n".join(str(n) for n in nums) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == answer, f"expected {answer!r}, got {out!r}"

    return TaskInstance(
        f"readsorted_{len(nums)}_{sum(nums)}", "multi-file",
        "The file numbers.txt has one integer per line. Write solution.py that reads numbers.txt and prints "
        "the integers in ASCENDING order, space-separated on ONE line (e.g. '1 3 5'). Run it to verify.",
        verify, setup=setup)


def gen_grep_count(rng: Random) -> TaskInstance:
    # text-processing (a different domain): count words containing a letter. Words vary -> non-hardcodable.
    import string
    words = ["".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(3, 6)))
             for _ in range(rng.randint(5, 9))]
    needle = rng.choice("abcde")
    answer = sum(1 for w in words if needle in w)

    def setup(ws: Path) -> None:
        (ws / "words.txt").write_text("\n".join(words) + "\n")

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "solution.py")
        except Exception as e:
            return False, f"could not run solution.py: {e}"
        return out == str(answer), f"expected {answer}, got {out!r}"

    return TaskInstance(
        f"grepcount_{needle}_{answer}", "multi-file",
        f"The file words.txt has one word per line. Write solution.py that reads words.txt and prints HOW "
        f"MANY words contain the letter '{needle}'. Run it to verify.", verify, setup=setup)


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


def gen_pond_tick(rng: Random) -> TaskInstance:
    """The bread tick WIRED TO placement (Icarus's strength): validate the layout, then run the economy."""
    n = rng.randint(4, 6)
    ticks = rng.randint(3, 6)
    start = rng.randint(5, 15)
    nb, ng = rng.randint(1, 3), rng.randint(1, 2)
    placed: "list[tuple[int, int]]" = []

    def place() -> "tuple[int, int]":
        while True:
            p = (rng.randint(0, n - 1), rng.randint(0, n - 1))
            if p not in placed:
                placed.append(p)
                return p

    bakeries = [place() for _ in range(nb)]
    nests = [place() for _ in range(ng)]
    if rng.random() > 0.6:  # inject an invalid placement
        bakeries.append((n + 1, 0) if rng.random() > 0.5 else bakeries[0])
    cells = bakeries + nests
    valid = all(0 <= x < n and 0 <= y < n for x, y in cells) and len(set(cells)) == len(cells)
    expected = str(start + ticks * (nb * 3 - ng)) if valid else "INVALID"
    layout = "; ".join([f"bakery at ({x},{y})" for x, y in bakeries]
                       + [f"nest at ({x},{y})" for x, y in nests])

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "pond.py")
        except Exception as e:
            return False, f"could not run pond.py: {e}"
        return out.strip() == expected, f"expected {expected}, got {out.strip()!r}"

    return TaskInstance(
        f"pondtick_{rng.randint(1000, 9999)}_{expected}", "game-logic",
        f"A goose pond has an {n}x{n} grid (valid cells 0..{n - 1}). Buildings: {layout}. Each tick a "
        f"bakery makes 3 bread and each nest's goose eats 1 bread. Start with {start} bread and run "
        f"{ticks} ticks. If ANY building is out-of-bounds OR two buildings share a cell, print ONLY "
        f"'INVALID'. Otherwise print ONLY the final bread total. Write pond.py and run it to verify.",
        verify)


def gen_water_access(rng: Random) -> TaskInstance:
    """A spatial One Pond rule (Icarus's logic strength): every nest must be near the pond's water."""
    n = rng.randint(5, 8)
    px, py = rng.randint(0, n - 1), rng.randint(0, n - 1)
    reach = rng.randint(2, 4)
    nests: "list[tuple[int, int]]" = []
    while len(nests) < rng.randint(2, 4):
        p = (rng.randint(0, n - 1), rng.randint(0, n - 1))
        if p != (px, py) and p not in nests:
            nests.append(p)
    safe = all(abs(x - px) + abs(y - py) <= reach for x, y in nests)
    expected = "SAFE" if safe else "UNSAFE"
    nest_str = "; ".join(f"({x},{y})" for x, y in nests)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "water.py")
        except Exception as e:
            return False, f"could not run water.py: {e}"
        return out.strip() == expected, f"expected {expected}, got {out.strip()!r}"

    return TaskInstance(
        f"wateraccess_{rng.randint(1000, 9999)}_{expected}", "game-logic",
        f"A goose pond sits at cell ({px},{py}) on an {n}x{n} grid. Nests are at: {nest_str}. A nest has "
        f"water access if its Manhattan distance to the pond (|dx|+|dy|) is at most {reach}. Print ONLY "
        f"'SAFE' if EVERY nest has water access, otherwise 'UNSAFE'. Write water.py and run it to verify.",
        verify)


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


def gen_predator_safety(rng: Random) -> TaskInstance:
    """Predator safety (a core One Pond rule): every nest must be guarded by a nearby fence."""
    n = rng.randint(6, 9)
    reach = rng.randint(2, 3)

    def rand_cells(k: int) -> "list[tuple[int, int]]":
        cells: "list[tuple[int, int]]" = []
        while len(cells) < k:
            p = (rng.randint(0, n - 1), rng.randint(0, n - 1))
            if p not in cells:
                cells.append(p)
        return cells

    nests = rand_cells(rng.randint(2, 4))
    fences = rand_cells(rng.randint(1, 3))
    safe = all(any(abs(nx - fx) + abs(ny - fy) <= reach for fx, fy in fences) for nx, ny in nests)
    expected = "SAFE" if safe else "UNSAFE"
    nest_str = "; ".join(f"({x},{y})" for x, y in nests)
    fence_str = "; ".join(f"({x},{y})" for x, y in fences)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "predator.py")
        except Exception as e:
            return False, f"could not run predator.py: {e}"
        return out.strip() == expected, f"expected {expected}, got {out.strip()!r}"

    return TaskInstance(
        f"predator_{rng.randint(1000, 9999)}_{expected}", "game-logic",
        f"On an {n}x{n} grid, goose nests are at: {nest_str}. Fences are at: {fence_str}. A nest is "
        f"guarded if its Manhattan distance (|dx|+|dy|) to at least one fence is at most {reach}. Print "
        f"ONLY 'SAFE' if EVERY nest is guarded, otherwise 'UNSAFE'. Write predator.py and run it to verify.",
        verify)


def gen_granary(rng: Random) -> TaskInstance:
    """The granary-synergy rule (a One Pond mechanic): each granary boosts every bakery's output."""
    bakeries = rng.randint(1, 5)
    granaries = rng.randint(0, 4)
    total = bakeries * (3 + granaries)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "granary.py")
        except Exception as e:
            return False, f"could not run granary.py: {e}"
        return out.strip() == str(total), f"expected {total}, got {out.strip()!r}"

    return TaskInstance(
        f"granary_{bakeries}b_{granaries}g", "game-logic",
        f"In a goose pond each bakery produces a base of 3 bread per tick, and each granary adds +1 to "
        f"EVERY bakery's output. With {bakeries} bakeries and {granaries} granaries, print ONLY the total "
        f"bread produced per tick. Write granary.py and run it to verify.",
        verify)


def gen_pond_score(rng: Random) -> TaskInstance:
    """The pond net-worth score (a One Pond mechanic): bread plus weighted building values."""
    bread = rng.randint(0, 30)
    counts = {k: rng.randint(0, 3) for k in ("bakery", "granary", "nest", "well")}
    weights = {"bakery": 10, "granary": 5, "nest": 3}
    total = bread + sum(counts[k] * weights.get(k, 2) for k in counts)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "score.py")
        except Exception as e:
            return False, f"could not run score.py: {e}"
        return out.strip() == str(total), f"expected {total}, got {out.strip()!r}"

    cs = ", ".join(f"{counts[k]} {k}" for k in ("bakery", "granary", "nest", "well"))
    return TaskInstance(
        f"pondscore_{bread}br_{counts['bakery']}{counts['granary']}{counts['nest']}{counts['well']}",
        "game-logic",
        f"Score a goose pond. It has {bread} bread and these buildings: {cs}. The score is the bread plus, "
        f"per building, 10 for a bakery, 5 for a granary, 3 for a nest, and 2 for anything else (a well). "
        f"Print ONLY the integer score. Write score.py and run it to verify.",
        verify)


def gen_pond_outcome(rng: Random) -> TaskInstance:
    """The layered win/lose evaluation (a composed One Pond rule): bread -> water -> safety -> thriving."""
    n = 8
    reach = rng.randint(2, 3)
    bread = rng.choice([0, rng.randint(1, 20), rng.randint(1, 20)])       # sometimes 0 (lost)
    kinds = ("bakery", "well", "nest", "fence", "granary")
    blds = [(rng.choice(kinds), rng.randint(0, n - 1), rng.randint(0, n - 1))
            for _ in range(rng.randint(2, 5))]

    def near(px: int, py: int, kind: str) -> bool:
        return any(abs(px - x) + abs(py - y) <= reach for k, x, y in blds if k == kind)

    if bread <= 0:
        expected = "lost"
    elif any(not near(x, y, "well") for k, x, y in blds if k == "bakery"):
        expected = "dry"
    elif any(not near(x, y, "fence") for k, x, y in blds if k == "nest"):
        expected = "unsafe"
    else:
        expected = "thriving"
    bstr = "; ".join(f"{k} at ({x},{y})" for k, x, y in blds)

    def verify(ws: Path) -> "tuple[bool, str]":
        try:
            rc, out, err = _run_py(ws, "outcome.py")
        except Exception as e:
            return False, f"could not run outcome.py: {e}"
        return out.strip() == expected, f"expected {expected}, got {out.strip()!r}"

    return TaskInstance(
        f"pondoutcome_{rng.randint(1000, 9999)}_{expected}", "game-logic",
        f"A goose pond has {bread} bread and these buildings: {bstr}. Manhattan distance is |dx|+|dy|. "
        f"Evaluate the pond and print ONLY ONE word, checking IN THIS ORDER: 'lost' if bread <= 0; else "
        f"'dry' if any bakery has NO well within distance {reach}; else 'unsafe' if any nest has NO fence "
        f"within distance {reach}; else 'thriving'. Write outcome.py and run it to verify.",
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


def gen_bakery_scene(rng: Random) -> TaskInstance:
    """Breadth: a scene with a BUILDING on the ground (not just a flat plane) — visual, routes to 30B."""
    def verify(ws: Path) -> "tuple[bool, str]":
        from game.godot.capture import green_dominance, render_gdscript, significant_colors
        gd_file = ws / "scene.gd"
        if not gd_file.exists():
            return False, "scene.gd not found"
        out = ws / "_render.png"
        ok, detail = render_gdscript(gd_file, out)
        if not ok:
            return False, detail
        try:
            gd = green_dominance(out)
            cols = significant_colors(out)
        except Exception as e:
            return False, f"could not read render: {e}"
        # a real bakery scene: green ground visible AND a distinct building region (>= 3 colours)
        if gd < 15:
            return False, f"no green ground (dominance {gd:.0f})"
        if cols < 3:
            return False, f"green ground but no building on it (only {cols} colour region(s))"
        return True, f"ground + building (green-dominance {gd:.0f}, {cols} colour regions)"

    return TaskInstance(
        f"bakery_scene_{rng.randint(1000, 9999)}", "render",
        "Write a Godot 4 GDScript file scene.gd (extends Node3D). In _ready(): a current orthogonal "
        "Camera3D aimed at the origin; a large green UNSHADED ground plane (PlaneMesh); AND a distinctly "
        "coloured (e.g. brown/tan) UNSHADED building box (BoxMesh, ~2-3 units, raised so it sits ON the "
        "ground) near the centre. The render must show the green ground WITH a building on it, not a "
        "bare plane.", verify)


def gen_pond_scene(rng: Random) -> TaskInstance:
    """The namesake One Pond scene: green LAND + a blue WATER pond + a building. Visual, routes to 30B."""
    def verify(ws: Path) -> "tuple[bool, str]":
        from game.godot.capture import color_fraction, render_gdscript, significant_colors
        gd_file = ws / "scene.gd"
        if not gd_file.exists():
            return False, "scene.gd not found"
        out = ws / "_render.png"
        ok, detail = render_gdscript(gd_file, out)
        if not ok:
            return False, detail
        try:
            land = color_fraction(out, "green")
            water = color_fraction(out, "blue")
            cols = significant_colors(out)
        except Exception as e:
            return False, f"could not read render: {e}"
        if land < 0.12:
            return False, f"no green land (green fraction {land:.2f})"
        if water < 0.04:
            return False, f"no blue pond water (blue fraction {water:.2f})"
        if cols < 3:
            return False, f"land + water but no building ({cols} colour regions)"
        return True, f"land {land:.2f} + water {water:.2f} + building ({cols} regions)"

    return TaskInstance(
        f"pond_scene_{rng.randint(1000, 9999)}", "render",
        "Write a Godot 4 GDScript scene.gd (extends Node3D). In _ready(): a current orthogonal Camera3D "
        "aimed at the origin; a large GREEN UNSHADED land plane (PlaneMesh); a smaller BLUE UNSHADED water "
        "plane (the pond) laid on top of the land near the centre (raised very slightly so it shows above "
        "the grass); and a distinctly coloured (brown) UNSHADED building box beside the pond. The render "
        "must show green land WITH a blue pond and a building.", verify)


def gen_pond_from_template(rng: Random) -> TaskInstance:
    """SPEED path: Icarus writes ONLY the build(root) content; the camera template is provided so the
    FAST resident model can build a real scene (see docs/SPEED.md). Verified by composing + rendering."""
    def verify(ws: Path) -> "tuple[bool, str]":
        from game.godot.capture import color_fraction, green_dominance, render_gdscript, significant_colors
        from game.godot.scene_template import compose_scene
        cand = None
        for p in sorted(ws.rglob("*.gd")):
            if p.name == "_composed_scene.gd":     # skip our own prior output, not the agent's content
                continue
            try:
                if "func build" in p.read_text():
                    cand = p
                    break
            except OSError:
                pass
        if cand is None:
            return False, "no .gd file with a build(root) function"
        scene = compose_scene(cand.read_text())
        sp = ws / "_composed_scene.gd"
        sp.write_text(scene)
        out = ws / "_render.png"
        ok, detail = render_gdscript(sp, out)
        if not ok:
            return False, f"composed scene failed to render: {detail}"
        try:
            land, water, cols = green_dominance(out), color_fraction(out, "blue"), significant_colors(out)
        except Exception as e:
            return False, f"could not read render: {e}"
        if land < 15:
            return False, f"no green land (dominance {land:.0f})"
        if water < 0.04:
            return False, f"no blue water pond (blue {water:.2f})"
        if cols < 3:
            return False, f"land + water but no building ({cols} regions)"
        return True, f"land {land:.0f} + water {water:.2f} + building ({cols} regions) [templated]"

    return TaskInstance(
        f"pondtmpl_{rng.randint(1000, 9999)}", "render",
        "Write content.gd containing ONLY `func build(root: Node3D) -> void:`. Two helpers already exist "
        "(do NOT redefine them, just call them):\n"
        "  add_plane(root, size: Vector2, color: Color, y: float = 0.0)  # a FLAT ground/water plane\n"
        "  add_box(root, size: Vector3, color: Color, pos: Vector3)      # a building box\n"
        "Build the One Pond: a large GREEN land plane (e.g. size Vector2(16,16)); a smaller BLUE water "
        "pond raised slightly so it shows (y = 0.1, e.g. size Vector2(6,6)); and a brown building box "
        "beside the pond (e.g. add_box(root, Vector3(2,2,2), Color(0.5,0.3,0.1), Vector3(4,1,0))). Do NOT "
        "add a Camera3D, _ready(), or your own meshes -- only call the helpers with Color.GREEN/Color.BLUE.",
        verify)


def default_generators() -> "list[Callable[[Random], TaskInstance]]":
    return [gen_sum, gen_reverse, gen_fib, gen_json, gen_fizzbuzz,
            gen_fix_bug, gen_fix_range_bug, gen_read_sum, gen_read_max, gen_read_evens, gen_read_sorted, gen_grep_count,
            gen_find_secret, gen_economy, gen_placement,
            gen_pond_tick, gen_water_access, gen_predator_safety, gen_granary, gen_pond_score,
            gen_pond_outcome, gen_gdscript, gen_render, gen_bakery_scene]


def sample_battery(seed: int = 0, per_generator: int = 1,
                   generators: "Optional[list[Callable[[Random], TaskInstance]]]" = None) -> "list[TaskInstance]":
    """A reproducible battery: `per_generator` fresh instances from each generator, seeded."""
    rng = Random(seed)
    gens = generators or default_generators()
    return [g(rng) for _ in range(per_generator) for g in gens]


# ---------------------------------------------------------------- the runner

def run_battery(model: "Optional[AgentModel]", instances: "list[TaskInstance]", workspace_root: Path, *,
                router=None, max_steps: int = 10, run_timeout: float = 20.0, use_notebook: bool = False,
                notebook: "Optional[Notebook]" = None, vision=None, render_fn=None) -> ScoreReport:
    """Drive the agent loop on each instance, verify the workspace, and score. Default is UNAIDED
    (no notebook) — the north-star capability measure. Pass a ``router`` (ModelRouter) to measure the
    ASSEMBLED Icarus: each task goes to its best model (visual→30B, logic→fast)."""
    if model is None and router is None:
        raise ValueError("run_battery needs a model or a router")
    report = ScoreReport()
    root = Path(workspace_root)
    for inst in instances:
        ws = root / inst.id
        ws.mkdir(parents=True, exist_ok=True)
        if inst.setup is not None:
            inst.setup(ws)  # seed a broken file / data file the task refers to
        task_model = router.for_task(inst.prompt) if router is not None else model
        try:
            res = run_agent(task_model, inst.prompt, ws, max_steps=max_steps, run_timeout=run_timeout,
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
