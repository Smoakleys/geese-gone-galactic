"""The monotonic quality ratchet.

Every accepted artifact becomes a regression fixture and contributes metric *floors*. The
one rule that makes the ratchet monotonic is expressed in ``raise_floors``:

    floor[metric] = max(old_floor, new_value)

A floor can only rise here. Lowering one is a separate, loud, logged operation
(``baseline_reset``) so that "quality silently regressed" — a documented past failure —
becomes structurally impossible: a silent drop simply isn't a code path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RegressionFixture:
    ticket_id: str
    artifact_hashes: dict[str, str]      # relpath -> sha256 of accepted bytes
    baseline_metrics: dict[str, float]
    applicable_checks: list[str] = field(default_factory=list)


class RatchetStore:
    """Persists regression fixtures + the monotonic floor manifest under a directory."""

    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "regression").mkdir(parents=True, exist_ok=True)
        self.floors_path = self.root / "floors.json"
        self.reset_log = self.root / "baseline_resets.log"

    # -- floors ------------------------------------------------------------------------

    def floors(self) -> dict[str, float]:
        if self.floors_path.exists():
            return json.loads(self.floors_path.read_text())
        return {}

    def raise_floors(self, metrics: dict[str, float]) -> dict[str, float]:
        """Monotonic update: each floor becomes max(old, new). Never lowers."""
        floors = self.floors()
        for k, v in metrics.items():
            floors[k] = max(floors.get(k, float("-inf")), float(v))
        self.floors_path.write_text(json.dumps(floors, indent=2, sort_keys=True))
        return floors

    def baseline_reset(self, metric: str, value: float, reason: str, actor: str) -> None:
        """The ONLY way a floor moves down. Loud and logged; audited by Stage C."""
        floors = self.floors()
        old = floors.get(metric)
        floors[metric] = float(value)
        self.floors_path.write_text(json.dumps(floors, indent=2, sort_keys=True))
        with self.reset_log.open("a") as fh:
            fh.write(json.dumps({"metric": metric, "old": old, "new": value,
                                 "reason": reason, "actor": actor}) + "\n")

    def check_floors(self, metrics: dict[str, float]) -> list[str]:
        """Return the names of any metrics that fall below their floor (regressions)."""
        floors = self.floors()
        return [k for k, floor in floors.items() if k in metrics and float(metrics[k]) < floor]

    # -- regression fixtures -----------------------------------------------------------

    def mint(self, fixture: RegressionFixture) -> Path:
        path = self.root / "regression" / f"{fixture.ticket_id}.json"
        path.write_text(json.dumps({
            "ticket_id": fixture.ticket_id,
            "artifact_hashes": fixture.artifact_hashes,
            "baseline_metrics": fixture.baseline_metrics,
            "applicable_checks": fixture.applicable_checks,
        }, indent=2, sort_keys=True))
        return path

    def fixtures(self) -> list[RegressionFixture]:
        out: list[RegressionFixture] = []
        for p in sorted((self.root / "regression").glob("*.json")):
            d = json.loads(p.read_text())
            out.append(RegressionFixture(
                ticket_id=d["ticket_id"],
                artifact_hashes=d["artifact_hashes"],
                baseline_metrics=d["baseline_metrics"],
                applicable_checks=d.get("applicable_checks", []),
            ))
        return out
