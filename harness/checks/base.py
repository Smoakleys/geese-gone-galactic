"""The Check contract.

A check is a pure function of ``(artifact_dir, ticket) -> CheckResult`` plus a declaration
of the fixtures that prove it works. The fixtures are not documentation — they are the
admission ticket: a check is inert until it demonstrably passes every good fixture and
fails every bad one (see ``registry.certify``).
"""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from harness.models import CheckResult, Ticket


class CheckCost(IntEnum):
    """Cost tier for Stage-A ordering. Cheaper tiers run first so an expensive pixel
    analysis (or, later, a Godot screenshot) never runs after a cheap syntax check has
    already condemned the artifact. The loop's Stage A fail-fasts on the first FAIL, so
    tiering turns "run everything" into "run the cheapest thing that can reject first."
    """

    STATIC = 0       # read files as text; no decode (syntax, json, manifest presence)
    STRUCTURAL = 1   # light metadata parse (image header, dimensions, file counts)
    DYNAMIC = 2       # full decode / pixel analysis / (Phase 2+) rendered screenshot


# Checks may omit ``cost``; the registry treats a missing tier as STRUCTURAL.
DEFAULT_COST = CheckCost.STRUCTURAL


@runtime_checkable
class Check(Protocol):
    id: str
    targets: list[str]           # ticket kinds or artifact globs this check applies to
    good_fixtures: list[Path]    # directories the check MUST pass
    bad_fixtures: list[Path]     # directories the check MUST fail
    cost: CheckCost              # Stage-A ordering tier (optional; defaults to STRUCTURAL)

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult: ...


def cost_of(check: Check) -> CheckCost:
    """The declared cost tier of a check, or the default if it declares none."""
    return CheckCost(getattr(check, "cost", DEFAULT_COST))
