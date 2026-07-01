"""Built-in deterministic checks for the walking skeleton.

Only one, deliberately trivial, check lives here for Phase 0.5: it exists to *exercise the
certification and Stage-A machinery end to end*, not to judge game quality. Real code/CV
checks replace and join it in Phase 1. The value proven here is structural: a check earns
its place in Stage A only by certifying against good/bad fixtures.
"""

from __future__ import annotations

from pathlib import Path

from harness.checks.base import Check
from harness.models import CheckResult, Result, Ticket

# Fixtures ship next to this package so the check is self-contained and certifiable offline.
_FIXTURES = Path(__file__).parent / "fixtures" / "non_empty_artifact"


class NonEmptyArtifactCheck(Check):
    """Passes iff the artifact directory contains at least one non-empty regular file.

    Trivial, but it has a real failure mode (a builder that produced nothing, or only empty
    stub files) and thus a real good/bad fixture pair — enough to prove certification works.
    """

    id = "non_empty_artifact"
    targets: list[str] = ["*"]

    def __init__(self) -> None:
        self.good_fixtures = [_FIXTURES / "good"]
        self.bad_fixtures = [_FIXTURES / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        artifact_dir = Path(artifact_dir)
        if not artifact_dir.exists():
            return CheckResult(self.id, Result.FAIL, f"artifact dir missing: {artifact_dir}")
        non_empty = [
            f for f in artifact_dir.rglob("*")
            if f.is_file() and f.name != "decision_log.jsonl" and f.stat().st_size > 0
        ]
        if non_empty:
            return CheckResult(
                self.id, Result.PASS,
                f"{len(non_empty)} non-empty artifact file(s)",
                artifacts=[str(p) for p in non_empty[:5]],
            )
        return CheckResult(self.id, Result.FAIL, "no non-empty artifact files produced")


def default_registry(lock_dir: Path):
    """Build a Registry pre-loaded with the built-in checks and certify it."""
    from harness.checks.registry import Registry

    reg = Registry(lock_dir)
    reg.register(NonEmptyArtifactCheck())
    reg.certify_all()
    return reg
