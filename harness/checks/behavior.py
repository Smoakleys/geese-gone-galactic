"""Deterministic behavioural check for logic tickets.

A subjective reviewer enforces only what a criterion *pins*, so an exact-output typo (e.g. ``'baker'``
instead of ``'bakery'``) can slip a loosely-worded criterion (seen on OP-6 and OP-8). This check makes
exact-output correctness MECHANICAL: for each ``{module, call, expect}`` example it imports the produced
module and requires ``call`` to equal ``expect`` exactly. It can't be talked around.

Examples come from ``artifact_dir/_behavior.json`` when present (so the check certifies against fixtures
with a fixed ticket) and otherwise from ``ticket.behavior`` (authored per ticket). No examples -> SKIP.
Fail-closed: a missing module, a raised exception, or any mismatch is a FAIL.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.checks.base import Check, CheckCost
from harness.models import CheckResult, Result, Ticket

_FIXTURES = Path(__file__).parent / "fixtures"


class PythonBehaviorCheck(Check):
    """Run authored input->output examples against the produced Python module; require exact results."""

    id = "python_behavior"
    # targets are matched against ticket.kind (registry._applies), NOT filenames -- so this must be "*"
    # to apply to every ticket kind. It was mistakenly ["*.py"], which never matches a kind and made the
    # check SKIP in the live pipeline (harness-mod-50). It SKIPs internally when the ticket has no behavior.
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC  # imports + executes the produced module

    def __init__(self) -> None:
        base = _FIXTURES / "python_behavior"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        d = Path(artifact_dir)
        spec_file = d / "_behavior.json"
        if spec_file.exists():
            try:
                examples = json.loads(spec_file.read_text(encoding="utf-8"))
            except Exception as e:
                return CheckResult(self.id, Result.FAIL, f"unreadable _behavior.json: {e}")
        else:
            examples = list(getattr(ticket, "behavior", []) or [])
        if not examples:
            return CheckResult(self.id, Result.SKIP, "no behavioural examples")

        for ex in examples:
            mod, call, expect = ex.get("module"), ex.get("call"), ex.get("expect")
            p = d / str(mod)
            if not p.is_file():
                return CheckResult(self.id, Result.FAIL, f"module {mod!r} not found")
            ns: dict = {}
            try:
                exec(compile(p.read_text(encoding="utf-8"), str(mod), "exec"), ns)
                got = eval(call, ns)  # noqa: S307 - gating the agent's own code, sandboxed workspace
            except Exception as e:
                return CheckResult(self.id, Result.FAIL,
                                   f"{mod}: {call} raised {type(e).__name__}: {e}", artifacts=[str(p)])
            if got != expect:
                return CheckResult(self.id, Result.FAIL,
                                   f"{mod}: {call} == {got!r}, expected {expect!r}", artifacts=[str(p)])

        return CheckResult(self.id, Result.PASS, f"{len(examples)} behavioural example(s) passed",
                           metrics={"behaviour_examples": float(len(examples))})
