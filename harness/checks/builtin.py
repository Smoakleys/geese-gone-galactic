"""Built-in deterministic checks for the walking skeleton.

Only one, deliberately trivial, check lives here for Phase 0.5: it exists to *exercise the
certification and Stage-A machinery end to end*, not to judge game quality. Real code/CV
checks replace and join it in Phase 1. The value proven here is structural: a check earns
its place in Stage A only by certifying against good/bad fixtures.
"""

from __future__ import annotations

from pathlib import Path

from harness.checks.base import Check, CheckCost
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
    cost = CheckCost.STATIC

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
                metrics={"non_empty_files": float(len(non_empty))},
            )
        return CheckResult(self.id, Result.FAIL, "no non-empty artifact files produced")


def default_registry(lock_dir: Path):
    """Build a Registry pre-loaded with the built-in checks and certify it.

    Registration order is the tie-break within a cost tier, so the most fundamental cheap
    check (``non_empty_artifact``) is registered first and fail-fasts an empty build before
    any code or image analysis runs. Image checks certify only where Pillow is importable;
    a machine without Pillow simply runs a smaller certified suite (they never wave art
    through — an uncertified check is inert).
    """
    from harness.checks.registry import Registry
    from harness.checks.behavior import PythonBehaviorCheck
    from harness.checks.code import PythonSyntaxCheck, JsonValidCheck

    reg = Registry(lock_dir)
    reg.register(NonEmptyArtifactCheck())      # STATIC, first — cheapest reject
    reg.register(PythonSyntaxCheck())          # STATIC
    reg.register(JsonValidCheck())             # STATIC
    reg.register(PythonBehaviorCheck())        # DYNAMIC — exact-output gate (SKIP unless ticket.behavior)
    for check in _optional_image_checks():     # STRUCTURAL / DYNAMIC, only if Pillow present
        reg.register(check)
    reg.certify_all()
    return reg


def _optional_image_checks() -> list[Check]:
    """The CV checks, or an empty list if Pillow is unavailable on this machine."""
    try:
        import PIL  # noqa: F401
    except Exception:
        return []
    from harness.checks.image import (
        ImageLoadableCheck,
        ImageMinResolutionCheck,
        ImageNotBlankCheck,
    )
    return [ImageLoadableCheck(), ImageMinResolutionCheck(), ImageNotBlankCheck()]
