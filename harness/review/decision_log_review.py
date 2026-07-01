"""Stage-C decision-log review — the taste→gate flywheel.

Stage B is deliberately blind to the builder's decision log so review stays adversarial.
Stage C is the opposite: it runs *after* acceptance, off the critical path, and its whole job
is to read the decision logs and the history of subjective Stage-B defects and ask "which of
these judgements should stop being subjective?" A defect that reviewers keep raising by hand
is a check waiting to be written — every time taste catches something the deterministic gate
missed, that becomes a candidate new check, so Stage A gets stricter over time and the
expensive human/model judgement is spent only on genuinely new questions.

This module does not *write* checks (that is a self-mod change, guarded by the validator). It
surfaces concrete, prioritized proposals a maintainer or Icarus can act on.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DefectRecord:
    ticket_id: str
    criterion: str
    detail: str


@dataclass(frozen=True)
class ProposedAdjustment:
    kind: str            # "new_check" | "tighten_rubric"
    signature: str       # the recurring defect signature this targets
    occurrences: int
    rationale: str
    suggested_check_id: str


@dataclass
class DecisionLogReview:
    threshold: int = 3   # a defect must recur this many times to earn a check proposal
    proposals: list[ProposedAdjustment] = field(default_factory=list)

    def analyze(self, defects: Iterable[DefectRecord]) -> list[ProposedAdjustment]:
        """Propose a deterministic check for every subjective defect that recurs >= threshold.

        Recurrence is counted by a normalized signature (criterion + first words of the
        detail) so slightly-reworded rejections of the same underlying problem still cluster.
        """
        counts: Counter[str] = Counter()
        examples: dict[str, DefectRecord] = {}
        for d in defects:
            sig = _signature(d)
            counts[sig] += 1
            examples.setdefault(sig, d)

        proposals: list[ProposedAdjustment] = []
        for sig, n in counts.most_common():
            if n < self.threshold:
                continue
            ex = examples[sig]
            proposals.append(ProposedAdjustment(
                kind="new_check",
                signature=sig,
                occurrences=n,
                rationale=(f"Reviewers rejected {n} artifacts for '{ex.detail}' on "
                           f"criterion {ex.criterion}; fold this into a deterministic check "
                           f"so Stage A catches it before a reviewer has to."),
                suggested_check_id=_check_id(sig),
            ))
        self.proposals = proposals
        return proposals


def load_defect_records(decision_log_path: Path, ticket_id: str) -> list[DefectRecord]:
    """Pull any reviewer-defect entries a builder recorded into its decision log.

    Builders log the defects they were handed for rework under ``{"defect": {...}}`` lines;
    Stage C harvests them across tickets to spot recurring subjective failures.
    """
    records: list[DefectRecord] = []
    p = Path(decision_log_path)
    if not p.exists():
        return records
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = entry.get("defect")
        if isinstance(d, dict) and "criterion" in d:
            records.append(DefectRecord(ticket_id, str(d["criterion"]), str(d.get("detail", ""))))
    return records


def _signature(d: DefectRecord) -> str:
    head = " ".join(d.detail.lower().split()[:6])
    return f"{d.criterion}:{head}"


def _check_id(signature: str) -> str:
    crit = signature.split(":", 1)[0].strip().lower()
    slug = "".join(ch if ch.isalnum() else "_" for ch in crit).strip("_") or "review"
    return f"auto_{slug}_check"
