"""Core data model for the harness.

Deliberately stdlib-only (dataclasses + hashlib + json) so the harness core is
importable anywhere with no third-party runtime dependency. Pydantic is a Phase-1
upgrade if/when schemas grow; the validation we actually need here — *coerce missing
or empty evidence to FAIL* — is expressed directly so it can never be relaxed by a
permissive parser.

Two anti-cheat mechanisms live in this module and are the reason it is code, not prose:

* ``criteria_hash`` — a sha256 over the *frozen* acceptance criteria. Computed once at
  freeze time and stored on the ticket. Any later edit to the criteria changes the hash;
  the Gatekeeper recomputes and refuses to act on a mismatch. This is what makes
  "criteria written before the build" enforceable rather than aspirational.
* ``Verdict`` default-FAIL — a verdict PASSes only if *every* stage-relevant criterion
  carries an explicit PASS with non-empty evidence. Missing keys, empty strings, and
  whitespace all coerce to FAIL. "Looks fine" cannot pass by construction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


# --------------------------------------------------------------------------------------
# Verdicts / results
# --------------------------------------------------------------------------------------


class Result(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class Stage(str, Enum):
    A = "A"  # deterministic checks
    B = "B"  # clean adversarial review
    C = "C"  # decision-log review (async, off critical path)


# --------------------------------------------------------------------------------------
# Ticket + acceptance criteria
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One independently-testable criterion, authored before the build starts."""

    id: str
    text: str
    stage: Stage
    check_hint: Optional[str] = None  # maps to a deterministic check id when applicable
    rubric_ref: Optional[str] = None

    def canonical(self) -> dict[str, Any]:
        # Order-stable, hash-stable projection. Only the *committed intent* is hashed;
        # transient fields (if any are added later) must be excluded here on purpose.
        return {
            "id": self.id,
            "text": self.text,
            "stage": self.stage.value,
            "check_hint": self.check_hint,
            "rubric_ref": self.rubric_ref,
        }


def compute_criteria_hash(criteria: list[AcceptanceCriterion]) -> str:
    """Deterministic sha256 over the ordered criteria block.

    The list order is part of the identity: reordering criteria is a change. Uses
    ``sort_keys`` on each criterion dict for field-order stability while preserving the
    author's list order.
    """
    payload = json.dumps(
        [c.canonical() for c in criteria],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TicketKind(str, Enum):
    ASSET = "asset"
    SYSTEM = "system"
    INTERACTION = "interaction"
    MIXED = "mixed"


@dataclass
class Ticket:
    """A bounded unit of game work with criteria frozen before the build.

    ``criteria_hash`` is None until :meth:`freeze` is called; after that the ticket is
    treated as read-only. The Gatekeeper independently recomputes the hash and aborts the
    iteration if it no longer matches (tamper detection).
    """

    id: str
    title: str
    kind: TicketKind
    acceptance_criteria: list[AcceptanceCriterion]
    references: list[str] = field(default_factory=list)
    # Optional deterministic behavioural examples for a logic ticket: each is
    # {"module": "<file>.py", "call": "<expr>", "expect": <value>}. Run by PythonBehaviorCheck to gate
    # exact-output correctness (catches typos a subjective reviewer misses). Not part of criteria_hash.
    behavior: list = field(default_factory=list)
    rubric_ref: Optional[str] = None
    created_by: str = "architect"
    criteria_hash: Optional[str] = None
    frozen: bool = False

    def freeze(self) -> str:
        """Mint the criteria hash and lock the ticket. Idempotent only if unchanged."""
        if self.frozen:
            raise ValueError(f"ticket {self.id} already frozen")
        self.criteria_hash = compute_criteria_hash(self.acceptance_criteria)
        self.frozen = True
        return self.criteria_hash

    def current_hash(self) -> str:
        """Recompute the hash from current criteria (used to detect post-freeze edits)."""
        return compute_criteria_hash(self.acceptance_criteria)

    def is_tampered(self) -> bool:
        """True if the ticket was frozen but its criteria no longer hash to the stored value."""
        if not self.frozen or self.criteria_hash is None:
            return False
        return self.current_hash() != self.criteria_hash

    def criteria_for_stage(self, stage: Stage) -> list[AcceptanceCriterion]:
        return [c for c in self.acceptance_criteria if c.stage == stage]


# --------------------------------------------------------------------------------------
# Check + build results
# --------------------------------------------------------------------------------------


@dataclass
class CheckResult:
    check_id: str
    result: Result
    evidence: str = ""
    artifacts: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    # Real numeric quality signals emitted by the check (e.g. min resolution, pixel
    # variance). The Gatekeeper mints these as monotonic ratchet floors on acceptance, so
    # "the art can only get sharper / less blank from here" becomes a structural floor, not
    # a hope. Only higher-is-better metrics belong here.
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.result == Result.PASS


@dataclass
class CriterionVerdict:
    """A reviewer's per-criterion judgement. PASS requires non-empty evidence."""

    id: str
    result: Result
    evidence: str = ""

    @property
    def is_effective_pass(self) -> bool:
        # The core anti-complacency rule: a PASS without real evidence is not a PASS.
        return self.result == Result.PASS and bool(self.evidence.strip())


@dataclass
class Defect:
    criterion: str
    severity: str  # "blocking" | "minor"
    detail: str
    repro: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.severity == "blocking"


@dataclass
class Verdict:
    """A reviewer's verdict for one stage. Consumed only by the Gatekeeper.

    Construct via :meth:`build` so the default-FAIL / empty-evidence coercion is applied
    uniformly. The public :attr:`verdict` is *derived*, never trusted from input.
    """

    ticket_id: str
    criteria_hash: str
    stage: Stage
    reviewer_id: str
    per_criterion: list[CriterionVerdict]
    defects: list[Defect] = field(default_factory=list)

    @property
    def verdict(self) -> Result:
        """Derived overall verdict. FAIL unless every required criterion effectively PASSes
        and there are no blocking defects. Never read a caller-supplied overall verdict."""
        if not self.per_criterion:
            return Result.FAIL  # nothing attested → fail by default
        if any(d.is_blocking for d in self.defects):
            return Result.FAIL
        return Result.PASS if all(c.is_effective_pass for c in self.per_criterion) else Result.FAIL

    @property
    def passed(self) -> bool:
        return self.verdict == Result.PASS

    @classmethod
    def build(
        cls,
        *,
        ticket: Ticket,
        stage: Stage,
        reviewer_id: str,
        per_criterion: list[CriterionVerdict],
        defects: Optional[list[Defect]] = None,
    ) -> "Verdict":
        """Assemble a verdict that covers exactly the stage-relevant criteria.

        Any stage criterion the reviewer failed to return is inserted as an explicit FAIL,
        so silence never reads as approval.
        """
        required = {c.id for c in ticket.criteria_for_stage(stage)}
        returned = {c.id: c for c in per_criterion}
        merged: list[CriterionVerdict] = []
        for cid in sorted(required):
            merged.append(returned.get(cid, CriterionVerdict(id=cid, result=Result.FAIL, evidence="")))
        if ticket.criteria_hash is None:
            raise ValueError("cannot build a verdict against an unfrozen ticket")
        return cls(
            ticket_id=ticket.id,
            criteria_hash=ticket.criteria_hash,
            stage=stage,
            reviewer_id=reviewer_id,
            per_criterion=merged,
            defects=list(defects or []),
        )

    def to_json(self) -> str:
        return json.dumps(_verdict_to_dict(self), indent=2, sort_keys=True)


def _verdict_to_dict(v: Verdict) -> dict[str, Any]:
    d = asdict(v)
    d["stage"] = v.stage.value
    d["verdict"] = v.verdict.value  # persist the derived value for audit, but recompute on load
    for c in d["per_criterion"]:
        c["result"] = c["result"].value if isinstance(c["result"], Result) else c["result"]
    return d


# --------------------------------------------------------------------------------------
# Builder seam (Icarus) — the loop only ever talks to this contract
# --------------------------------------------------------------------------------------


class BuildStatus(str, Enum):
    COMPLETED = "COMPLETED"  # a *claim* only — the gate decides
    GAVE_UP = "GAVE_UP"      # first-class: triggers escape-hatch + Icarus-upgrade ticket


@dataclass
class BuildPacket:
    """Everything the builder is given. ``writable_root`` is the ONLY path it may write."""

    ticket: Ticket
    writable_root: str
    references: list[str] = field(default_factory=list)
    defects: list[Defect] = field(default_factory=list)  # empty on round 1
    tool_manifest: list[str] = field(default_factory=list)
    budget: Optional[int] = None


@dataclass
class BuildResult:
    """The builder's output. ``status`` carries zero authority; the gate decides."""

    status: BuildStatus
    artifact_dir: str
    decision_log_path: Optional[str] = None
    notes: str = ""
