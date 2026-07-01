"""Plateau detection — the anti-coasting tooth as a concrete numeric trigger.

The failure mode: the loop spins round after round making cosmetic changes while the real
defect never moves, quietly burning budget and never escalating. A plateau is defined here in
two measurable ways, either of which fires:

* **Stuck signature** — the same blocking-defect signature recurs for ``window`` consecutive
  rounds (the reviewer keeps rejecting for the same reason).
* **No score gain** — the best objective score (e.g. the visual-gate score) has not improved
  by at least ``min_gain`` across the last ``window`` rounds.

On a plateau the loop diverts to ``PLATEAU_ESCALATE`` (escape-hatch) instead of iterating
forever. This is deterministic and unit-testable — no thresholds hidden in prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlateauDetector:
    window: int = 3
    min_gain: float = 0.01
    _signatures: list[str] = field(default_factory=list)
    _scores: list[float] = field(default_factory=list)

    def record(self, *, signature: str, score: Optional[float] = None) -> None:
        self._signatures.append(signature)
        if score is not None:
            self._scores.append(float(score))

    def stuck_signature(self) -> bool:
        if len(self._signatures) < self.window:
            return False
        last = self._signatures[-self.window:]
        return len(set(last)) == 1 and last[0] != ""

    def no_score_gain(self) -> bool:
        if len(self._scores) < self.window:
            return False
        recent = self._scores[-self.window:]
        return (max(recent) - recent[0]) < self.min_gain

    def plateaued(self) -> bool:
        """Fire if either plateau condition holds. Score gate only applies once we have scores."""
        if self.stuck_signature():
            return True
        if self._scores and self.no_score_gain():
            return True
        return False


def defect_signature(defects) -> str:
    """Stable signature for a round's blocking defects (order-independent)."""
    keys = sorted(f"{d.criterion}:{d.detail}" for d in defects if getattr(d, "is_blocking", False))
    return "|".join(keys)
