"""Flywheel metrics: autonomy rate + plateau detection.

Minimal for the walking skeleton; real logging/dashboard wiring lands in Phase 3. The
north-star is Icarus autonomy rate — the share of gate-passing iterations produced with zero
Claude (escape-hatch) building.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metrics:
    accepted: int = 0
    escape_hatch_builds: int = 0
    review_rounds: list[int] = field(default_factory=list)

    def record(self, *, rounds: int, escape_hatch: bool) -> None:
        self.accepted += 1
        self.review_rounds.append(rounds)
        if escape_hatch:
            self.escape_hatch_builds += 1

    @property
    def autonomy_rate(self) -> float:
        """Share of accepted work with no escape-hatch (Claude) building. Target -> 1.0."""
        if self.accepted == 0:
            return 0.0
        return (self.accepted - self.escape_hatch_builds) / self.accepted
