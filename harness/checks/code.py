"""Deterministic *code* checks — the cheap STATIC tier of Stage A.

These read candidate files as text and reject the categories of defect a builder most
commonly ships: source that does not parse, config/data that is not valid JSON. They are
pure functions of the artifact directory, they certify against committed good/bad fixtures,
and they short-circuit the rest of Stage A when they FAIL (cheapest tier, so nothing
expensive runs behind a broken file).

A check returns SKIP when the artifact contains none of its target files, so a text-only or
image-only ticket is not failed by a code check that simply does not apply.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from harness.checks.base import Check, CheckCost
from harness.models import CheckResult, Result, Ticket

_FIXTURES = Path(__file__).parent / "fixtures"

# Unambiguous placeholder/template markers that COMPILE but are non-solutions -- a model sometimes emits the
# tool protocol's `body:` example literally (`<code>`), or a template stub ("YOUR CODE HERE"). These never
# appear in real solved code, so flagging them has near-zero false-positive risk. Complements agent-side
# harness-mod-64 (which rejects a `<...>` WRITE body) by catching the class at the final gate too, incl.
# placeholder PHRASES the write-check doesn't see.
_STUB_LINE = re.compile(r"^\s*<[^>\n]{1,60}>\s*$", re.MULTILINE)          # a lone `<code>` / `<file contents>`
_STUB_PHRASE = re.compile(r"YOUR CODE HERE|TODO:\s*implement|REPLACE THIS|IMPLEMENT ME HERE", re.IGNORECASE)

# The decision log is builder-private and never a judged artifact.
_IGNORE = {"decision_log.jsonl"}


def _files(artifact_dir: Path, suffix: str) -> list[Path]:
    return [
        f for f in sorted(artifact_dir.rglob(f"*{suffix}"))
        if f.is_file() and f.name not in _IGNORE
    ]


class PythonSyntaxCheck(Check):
    """Every ``*.py`` file in the artifact must parse (``ast.parse``).

    Catches the single most common broken build: source that a downstream import would
    crash on. SKIPs when the artifact ships no Python.
    """

    id = "python_syntax"
    targets: list[str] = ["*"]
    cost = CheckCost.STATIC

    def __init__(self) -> None:
        base = _FIXTURES / "python_syntax"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        artifact_dir = Path(artifact_dir)
        py = _files(artifact_dir, ".py")
        if not py:
            return CheckResult(self.id, Result.SKIP, "no Python files in artifact")
        for f in py:
            try:
                src = f.read_text()
            except (UnicodeDecodeError, OSError) as e:  # a binary/undecodable ".py" is a defect
                return CheckResult(self.id, Result.FAIL, f"{f.name}: unreadable as text: {e}",
                                   artifacts=[str(f)])
            try:
                ast.parse(src, filename=str(f))
            except SyntaxError as e:
                return CheckResult(
                    self.id, Result.FAIL,
                    f"{f.name}: syntax error at line {e.lineno}: {e.msg}",
                    artifacts=[str(f)],
                )
            except ValueError as e:  # e.g. source containing null bytes — parse can't, so FAIL
                return CheckResult(self.id, Result.FAIL, f"{f.name}: not valid Python source: {e}",
                                   artifacts=[str(f)])
        return CheckResult(
            self.id, Result.PASS, f"{len(py)} Python file(s) parse cleanly",
            artifacts=[str(p) for p in py[:5]], metrics={"python_files": float(len(py))},
        )


class NoStubContentCheck(Check):
    """Every ``*.py`` file must be a real solution, not a placeholder/template stub.

    Catches the "compiles but does nothing" submission: a lone ``<code>``/``<file contents>`` placeholder
    line, or a template marker (``YOUR CODE HERE``, ``TODO: implement``). These pass ``python_syntax`` yet
    are non-solutions. Conservative by design (only unambiguous markers) so real code is never failed.
    SKIPs when the artifact ships no Python.
    """

    id = "no_stub_content"
    targets: list[str] = ["*"]
    cost = CheckCost.STATIC

    def __init__(self) -> None:
        base = _FIXTURES / "no_stub_content"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        artifact_dir = Path(artifact_dir)
        py = _files(artifact_dir, ".py")
        if not py:
            return CheckResult(self.id, Result.SKIP, "no Python files in artifact")
        for f in py:
            try:
                src = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue  # python_syntax owns unreadable files; don't double-fail here
            m = _STUB_LINE.search(src) or _STUB_PHRASE.search(src)
            if m:
                return CheckResult(
                    self.id, Result.FAIL,
                    f"{f.name}: placeholder/stub content, not a real solution: {m.group(0).strip()!r}",
                    artifacts=[str(f)],
                )
        return CheckResult(
            self.id, Result.PASS, f"{len(py)} Python file(s) are real (no placeholder stubs)",
            artifacts=[str(p) for p in py[:5]],
        )


class JsonValidCheck(Check):
    """Every ``*.json`` file in the artifact must be valid JSON. SKIPs when none exist."""

    id = "json_valid"
    targets: list[str] = ["*"]
    cost = CheckCost.STATIC

    def __init__(self) -> None:
        base = _FIXTURES / "json_valid"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        artifact_dir = Path(artifact_dir)
        docs = _files(artifact_dir, ".json")
        if not docs:
            return CheckResult(self.id, Result.SKIP, "no JSON files in artifact")
        for f in docs:
            try:
                text = f.read_text()
            except (UnicodeDecodeError, OSError) as e:  # a binary/undecodable ".json" is a defect
                return CheckResult(self.id, Result.FAIL, f"{f.name}: unreadable as text: {e}",
                                   artifacts=[str(f)])
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                return CheckResult(
                    self.id, Result.FAIL,
                    f"{f.name}: invalid JSON at line {e.lineno} col {e.colno}: {e.msg}",
                    artifacts=[str(f)],
                )
        return CheckResult(
            self.id, Result.PASS, f"{len(docs)} JSON file(s) valid",
            artifacts=[str(p) for p in docs[:5]],
        )
