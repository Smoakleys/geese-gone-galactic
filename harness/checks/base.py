"""The Check contract.

A check is a pure function of ``(artifact_dir, ticket) -> CheckResult`` plus a declaration
of the fixtures that prove it works. The fixtures are not documentation — they are the
admission ticket: a check is inert until it demonstrably passes every good fixture and
fails every bad one (see ``registry.certify``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from harness.models import CheckResult, Ticket


@runtime_checkable
class Check(Protocol):
    id: str
    targets: list[str]           # ticket kinds or artifact globs this check applies to
    good_fixtures: list[Path]    # directories the check MUST pass
    bad_fixtures: list[Path]     # directories the check MUST fail

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult: ...
