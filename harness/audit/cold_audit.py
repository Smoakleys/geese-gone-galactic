"""Cold audits — periodic, unannounced re-verification of accepted work that hard-blocks.

Acceptance is not forever. A cold audit re-opens already-committed artifacts and re-proves
them from scratch, so quality that rotted (a check weakened, a dependency shifted, a fixture
that no longer holds) is caught rather than trusted indefinitely. Two independent lenses:

* **Mechanical** — re-run the certified check suite + accepted-byte hashes over every
  regression fixture (delegates to ``run_regression_suite``).
* **Adversarial (optional)** — if given a fresh reviewer and a way to look up the original
  ticket, rebuild the isolated review packet from the *committed* artifact and re-review it.
  A model that accepted it once gets no say; this is a new, cold judgement.

Any finding makes ``AuditReport.blocked`` true. The intended wiring (Phase 3 control surface)
is that a blocked audit halts further acceptances until resolved — findings hard-block, they
are not advisory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from harness.checks.registry import Registry
from harness.gatekeeper import Gatekeeper, run_regression_suite
from harness.models import Ticket
from harness.review.base import Reviewer
from harness.review.packet_builder import IsolationViolation, build_review_packet


@dataclass(frozen=True)
class AuditFinding:
    ticket_id: str
    kind: str          # "regression" | "review" | "error"
    detail: str


@dataclass
class AuditReport:
    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.findings)

    def summary(self) -> str:
        if not self.findings:
            return "cold audit clean"
        return "; ".join(f"[{f.kind}] {f.ticket_id}: {f.detail}" for f in self.findings)


def cold_audit(
    gatekeeper: Gatekeeper,
    registry: Registry,
    *,
    reviewer: Optional[Reviewer] = None,
    ticket_provider: Optional[Callable[[str], Optional[Ticket]]] = None,
) -> AuditReport:
    """Re-verify every accepted regression fixture. Returns a report; ``blocked`` iff findings."""
    report = AuditReport()

    # 1) mechanical: hashes + certified checks must still hold on the committed bytes.
    for line in run_regression_suite(gatekeeper, registry):
        tid = line.split(":", 1)[0].split()[0]
        report.findings.append(AuditFinding(tid, "regression", line))

    # 2) adversarial re-review of the committed artifact (cold, fresh reviewer).
    if reviewer is not None and ticket_provider is not None:
        for fx in gatekeeper.ratchet.fixtures():
            accepted_dir = gatekeeper.accepted_root / fx.ticket_id
            ticket = ticket_provider(fx.ticket_id)
            if ticket is None or not accepted_dir.exists():
                continue
            try:
                packet = build_review_packet(ticket=ticket, artifact_dir=accepted_dir)
                verdict = reviewer.review(packet, ticket)
            except IsolationViolation as e:
                report.findings.append(AuditFinding(fx.ticket_id, "error", str(e)))
                continue
            if not verdict.passed:
                blocking = "; ".join(d.detail for d in verdict.defects if d.is_blocking)
                report.findings.append(AuditFinding(
                    fx.ticket_id, "review",
                    f"cold re-review FAILed: {blocking or 'no evidence on re-review'}",
                ))
    return report
