"""Reviewer isolation as a *construction* guarantee, not a promise.

The Stage-B reviewer must see only: the artifact files, the rubric text, the hash-verified
acceptance criteria, and the references. It must NEVER see the builder's decision log, notes,
prior-round verdicts, or any loop memory — otherwise "zero-context adversarial review"
degrades into "review of the builder's own justifications."

We enforce this by *building the packet from a whitelist* and then asserting the packet's
provenance is exactly that whitelist. The forbidden inputs are never loaded, so they cannot
leak; the assertion is belt-and-suspenders that converts intent into a checkable invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness.models import AcceptanceCriterion, Stage, Ticket

# Filenames that must never enter a review packet. Kept explicit so the ban is auditable.
FORBIDDEN_ARTIFACT_NAMES = {"decision_log.jsonl"}


class IsolationViolation(RuntimeError):
    pass


@dataclass
class ReviewPacket:
    ticket_id: str
    criteria_hash: str
    stage: Stage
    criteria: list[AcceptanceCriterion]
    rubric_text: str
    reference_paths: list[str]
    artifact_files: dict[str, str]  # relpath -> contents
    provenance: set[str] = field(default_factory=set)


def build_review_packet(
    *,
    ticket: Ticket,
    artifact_dir: Path,
    rubric_text: str = "",
) -> ReviewPacket:
    """Assemble a Stage-B packet from the whitelist and verify nothing forbidden leaked in.

    Raises ``IsolationViolation`` if the ticket is tampered/unfrozen or if a forbidden file
    (e.g. the decision log) reached the artifact set.
    """
    if ticket.criteria_hash is None:
        raise IsolationViolation("cannot review against an unfrozen ticket")
    if ticket.is_tampered():
        raise IsolationViolation("ticket criteria changed after freeze")

    artifact_dir = Path(artifact_dir)
    artifact_files: dict[str, str] = {}
    provenance: set[str] = set()
    for f in sorted(artifact_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.name in FORBIDDEN_ARTIFACT_NAMES:
            continue  # never load the decision log into a review packet
        rel = f.relative_to(artifact_dir).as_posix()
        try:
            artifact_files[rel] = f.read_text()
        except UnicodeDecodeError:
            artifact_files[rel] = f"<binary {f.stat().st_size} bytes>"
        provenance.add(f"artifact:{rel}")

    provenance.add(f"criteria_hash:{ticket.criteria_hash}")
    provenance.add("rubric")
    for r in ticket.references:
        provenance.add(f"reference:{r}")

    packet = ReviewPacket(
        ticket_id=ticket.id,
        criteria_hash=ticket.criteria_hash,
        stage=Stage.B,
        criteria=ticket.criteria_for_stage(Stage.B),
        rubric_text=rubric_text,
        reference_paths=list(ticket.references),
        artifact_files=artifact_files,
        provenance=provenance,
    )
    _assert_isolated(packet)
    return packet


def _assert_isolated(packet: ReviewPacket) -> None:
    """Provenance must be exactly {artifacts, criteria_hash, rubric, references}. Nothing else."""
    for token in packet.provenance:
        kind = token.split(":", 1)[0]
        if kind not in {"artifact", "criteria_hash", "rubric", "reference"}:
            raise IsolationViolation(f"forbidden provenance in review packet: {token!r}")
    for rel in packet.artifact_files:
        name = rel.rsplit("/", 1)[-1]
        if name in FORBIDDEN_ARTIFACT_NAMES:
            raise IsolationViolation(f"forbidden artifact leaked into packet: {rel!r}")
