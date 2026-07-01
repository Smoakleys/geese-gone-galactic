"""The Gatekeeper — the *only* code path in the system with commit authority.

Nothing else in the harness calls ``git commit`` or writes to the protected tree. Builders
write to gitignored staging; reviewers only emit verdicts. The Gatekeeper is handed a frozen
ticket, the staging dir, the Stage-A results and the Stage-B verdict, and it commits **iff**:

  1. the ticket is not tampered (recomputed criteria_hash matches the frozen value), AND
  2. the Stage-B verdict's criteria_hash matches the frozen ticket (verdict is for THIS spec),
     AND
  3. the Stage-B verdict passes (derived, default-FAIL), AND
  4. Stage A passed, AND
  5. no measured quality metric falls below an established ratchet floor (a regression is
     refused before it can touch the protected tree — the enforcement half of the ratchet).

Only then does it promote staging -> protected tree, ``git commit``, and mint the regression
fixture. Any failure short-circuits with no commit. This is why "the builder cannot approve
its own work" is a property of the wiring, not of anyone's good behaviour.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harness.checks.registry import Registry, stage_a_passed
from harness.models import CheckResult, Result, Ticket, Verdict
from harness.ratchet import RatchetStore, RegressionFixture
from harness.review.packet_builder import FORBIDDEN_ARTIFACT_NAMES
from harness.states import State


class GateAborted(RuntimeError):
    """Raised when the Gatekeeper refuses to commit due to tampering."""

    def __init__(self, state: State, reason: str):
        super().__init__(reason)
        self.state = state
        self.reason = reason


@dataclass
class CommitOutcome:
    committed: bool
    state: State
    reason: str
    accepted_dir: Optional[Path] = None
    git_sha: Optional[str] = None
    fixture_path: Optional[Path] = None


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Gatekeeper:
    def __init__(self, repo_root: Path, accepted_subdir: str = "game/accepted",
                 ratchet_dir: Optional[Path] = None):
        self.repo_root = Path(repo_root)
        self.accepted_root = self.repo_root / accepted_subdir
        self.ratchet = RatchetStore(ratchet_dir or (self.repo_root / "harness" / "checks" / "fixtures"))

    # -- the one privileged operation --------------------------------------------------

    def try_commit(
        self,
        *,
        ticket: Ticket,
        staging_dir: Path,
        registry: Registry,
        stage_a_results: list[CheckResult],
        verdict_b: Verdict,
    ) -> CommitOutcome:
        staging_dir = Path(staging_dir)

        # (1) tamper check on the ticket itself
        if ticket.criteria_hash is None:
            raise GateAborted(State.ABORTED_TAMPER, "ticket not frozen")
        if ticket.is_tampered():
            raise GateAborted(State.ABORTED_TAMPER, "ticket criteria changed after freeze")

        # (2) the verdict must be for THIS frozen spec
        if verdict_b.criteria_hash != ticket.criteria_hash:
            raise GateAborted(State.ABORTED_TAMPER,
                              "verdict criteria_hash does not match frozen ticket")

        # (3)+(4) gates — no commit unless both stages passed
        if not stage_a_passed(stage_a_results):
            return CommitOutcome(False, State.REWORK, "stage A failed")
        if not verdict_b.passed:
            return CommitOutcome(False, State.REWORK, "stage B failed")

        # (5) ratchet floor gate — the enforcement half of the monotonic ratchet.
        # ``raise_floors`` keeps a floor from dropping in *storage*; this refuses to accept an
        # artifact whose measured quality has dropped *below* an established floor at all. Run
        # BEFORE any promotion or commit so a regression never touches the protected tree.
        candidate_metrics = self._baseline_metrics(staging_dir, ticket.id, stage_a_results)
        violations = self.ratchet.check_floors(candidate_metrics)
        if violations:
            floors = self.ratchet.floors()
            detail = ", ".join(
                f"{m} {candidate_metrics[m]:g} < floor {floors[m]:g}" for m in sorted(violations))
            return CommitOutcome(False, State.REWORK, f"ratchet floor regression: {detail}")

        # --- promote staging -> protected tree ----------------------------------------
        accepted_dir = self.accepted_root / ticket.id
        if accepted_dir.exists():
            shutil.rmtree(accepted_dir)
        accepted_dir.mkdir(parents=True, exist_ok=True)

        artifact_hashes: dict[str, str] = {}
        for f in sorted(staging_dir.rglob("*")):
            if not f.is_file() or f.name in FORBIDDEN_ARTIFACT_NAMES:
                continue  # decision log never enters the committed artifact tree
            rel = f.relative_to(staging_dir)
            dst = accepted_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            artifact_hashes[rel.as_posix()] = _sha256_file(dst)

        git_sha = self._git_commit(accepted_dir, ticket)

        # --- ratchet: mint fixture + raise floors -------------------------------------
        # ``candidate_metrics`` was measured from the same bytes just promoted (identical file
        # set: staging minus the forbidden decision log), so it is the artifact's true baseline.
        metrics = candidate_metrics
        self.ratchet.raise_floors(metrics)
        fixture = RegressionFixture(
            ticket_id=ticket.id,
            artifact_hashes=artifact_hashes,
            baseline_metrics=metrics,
            applicable_checks=[c.id for c in registry.certified_checks()],
        )
        fixture_path = self.ratchet.mint(fixture)

        return CommitOutcome(True, State.DONE, "committed", accepted_dir, git_sha, fixture_path)

    # -- helpers -----------------------------------------------------------------------

    def _baseline_metrics(self, source_dir: Path, tid: str,
                          results: list[CheckResult]) -> dict[str, float]:
        # Count only the files that will actually be promoted: real files, non-empty, and not
        # the forbidden decision log — so metrics measured pre-promotion from staging match the
        # committed artifact exactly.
        non_empty = sum(
            1 for f in Path(source_dir).rglob("*")
            if f.is_file() and f.name not in FORBIDDEN_ARTIFACT_NAMES and f.stat().st_size > 0)
        metrics: dict[str, float] = {
            f"{tid}.non_empty_files": float(non_empty),
            f"{tid}.checks_passed": float(sum(1 for r in results if r.result == Result.PASS)),
        }
        # Fold in the real numeric quality signals each certified check emitted (min
        # resolution, pixel variance, ...). These become monotonic floors: this artifact can
        # never be re-accepted below the sharpness it was first accepted at.
        for r in results:
            for key, value in r.metrics.items():
                metrics[f"{tid}.{key}"] = float(value)
        return metrics

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def _git_commit(self, accepted_dir: Path, ticket: Ticket) -> str:
        self._git("add", str(accepted_dir.relative_to(self.repo_root)))
        self._git("commit", "-m", f"accept {ticket.id}: {ticket.title}",
                  "--author", "harness-gatekeeper <gatekeeper@ggg.local>")
        return self._git("rev-parse", "HEAD")


# -- ratchet suite (verification item 4): accepted artifacts can never silently regress ----


def run_regression_suite(gatekeeper: Gatekeeper, registry: Registry) -> list[str]:
    """Re-verify every accepted artifact against the certified checks + stored hashes.

    Returns a list of human-readable regression descriptions (empty == green). A reintroduced
    defect in a committed artifact — or any byte change from the accepted hash — is caught
    here automatically.
    """
    from harness.models import TicketKind, Ticket as _T

    regressions: list[str] = []
    for fx in gatekeeper.ratchet.fixtures():
        accepted_dir = gatekeeper.accepted_root / fx.ticket_id
        # 1) equivalence: committed bytes must still match the accepted hashes
        for rel, expected in fx.artifact_hashes.items():
            f = accepted_dir / rel
            if not f.exists():
                regressions.append(f"{fx.ticket_id}:{rel} missing")
            elif _sha256_file(f) != expected:
                regressions.append(f"{fx.ticket_id}:{rel} changed from accepted baseline")
        # 2) semantic: certified checks must still PASS on the accepted artifact
        stub = _T(id=fx.ticket_id, title="regression", kind=TicketKind.MIXED, acceptance_criteria=[])
        for res in registry.run_stage_a(accepted_dir, stub):
            if res.result == Result.FAIL:
                regressions.append(f"{fx.ticket_id}: check {res.check_id} now FAILs: {res.evidence}")
    return regressions
