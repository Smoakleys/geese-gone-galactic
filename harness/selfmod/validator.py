"""The self-modification validator — the gate on Opus editing the harness itself.

Tooth #4 in code: the same rigor the harness applies to game work, it applies to changes to
*itself*, with no ``--force`` and no author exemption. A candidate harness change is admitted
only if every invariant below holds; otherwise it is rejected and never merged.

Invariants enforced:

* **Suite stays green** — the full certified check suite re-verifies every accepted
  regression fixture (``run_regression_suite`` returns empty).
* **New checks certify** — certification is *recomputed from scratch* (never trusting the
  candidate's possibly hand-edited ``registry.lock``); any registered check that fails
  certification rejects the change. This is the "run the gate from the base snapshot, not the
  candidate" property: we don't believe the candidate's claim that its check is good, we
  re-prove it.
* **No silent floor drop / fixture deletion** — a floor may only fall, or a regression
  fixture disappear, if a matching ``baseline_reset`` was logged. A silent drop is rejected.
* **Changelog present** — a diff touching ``harness/`` must include a ``HARNESS_CHANGELOG.md``
  entry in the same change.

On accept, a revert token is recorded so the change is undoable with one command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.checks.registry import Registry
from harness.gatekeeper import Gatekeeper, run_regression_suite


CHANGELOG = "harness/HARNESS_CHANGELOG.md"


@dataclass
class ValidationResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)

    def require(self, condition: bool, reason: str) -> None:
        if not condition:
            self.ok = False
            self.reasons.append(reason)


def _changelog_touched_but_missing(changed_paths: list[str]) -> bool:
    touches_harness = any(
        p.startswith("harness/") and p != CHANGELOG and not p.endswith("registry.lock")
        for p in changed_paths
    )
    return touches_harness and CHANGELOG not in changed_paths


def validate_change(
    *,
    registry: Registry,
    gatekeeper: Gatekeeper,
    changed_paths: list[str],
    prev_floors: Optional[dict[str, float]] = None,
    prev_fixture_ids: Optional[set[str]] = None,
) -> ValidationResult:
    """Validate a candidate harness change. Returns ``ValidationResult(ok=..., reasons=[...])``."""
    result = ValidationResult(ok=True)

    # 1) changelog discipline (mechanical, cheap — check first)
    result.require(
        not _changelog_touched_but_missing(changed_paths),
        f"diff touches harness/ without a {CHANGELOG} entry",
    )

    # 2) re-prove certification from scratch (do not trust the candidate's registry.lock)
    outcomes = registry.certify_all()
    uncertified = [o for o in outcomes if not o.certified]
    result.require(
        not uncertified,
        "uncertified/broken check(s): " + ", ".join(f"{o.check_id} ({o.reason})" for o in uncertified),
    )

    # 3) suite must be green against every accepted regression fixture
    regressions = run_regression_suite(gatekeeper, registry)
    result.require(not regressions, "regression suite not green: " + "; ".join(regressions))

    # 4) no silent floor drop
    if prev_floors is not None:
        now = gatekeeper.ratchet.floors()
        reset_metrics = _logged_reset_metrics(gatekeeper)
        for metric, old in prev_floors.items():
            new = now.get(metric)
            if new is not None and new < old and metric not in reset_metrics:
                result.require(False, f"floor for {metric!r} dropped {old}->{new} without baseline_reset")

    # 5) no silent regression-fixture deletion
    if prev_fixture_ids is not None:
        now_ids = {f.ticket_id for f in gatekeeper.ratchet.fixtures()}
        removed = prev_fixture_ids - now_ids
        if removed:
            reset_metrics = _logged_reset_metrics(gatekeeper)
            # deletion is only allowed alongside an explicit reset naming the fixture
            for tid in removed:
                if not any(tid in m for m in reset_metrics):
                    result.require(False, f"regression fixture {tid!r} deleted without baseline_reset")

    return result


def _logged_reset_metrics(gatekeeper: Gatekeeper) -> set[str]:
    log = gatekeeper.ratchet.reset_log
    if not log.exists():
        return set()
    metrics: set[str] = set()
    for line in log.read_text().splitlines():
        if line.strip():
            metrics.add(json.loads(line)["metric"])
    return metrics


# -- revert bookkeeping ----------------------------------------------------------------


def record_accept(repo_root: Path, n: int, git_sha: str) -> None:
    """Record a revert token mapping harness-mod-<n> -> git sha (one-command revert source)."""
    log = Path(repo_root) / "harness" / "reverts.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as fh:
        fh.write(json.dumps({"n": n, "sha": git_sha}) + "\n")


def sha_for(repo_root: Path, n: int) -> Optional[str]:
    log = Path(repo_root) / "harness" / "reverts.log"
    if not log.exists():
        return None
    for line in log.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            if d["n"] == n:
                return d["sha"]
    return None
