"""The iteration state machine.

The whole governance thesis reduces to one graph property, asserted here in code:
**the only edge into ``COMMIT_PENDING`` comes from ``STAGE_B_PASS``, and ``DONE`` is
unreachable except through ``COMMIT_PENDING``.** No agent can construct a transition; the
loop advances state and the Gatekeeper alone owns the commit edge.
"""

from __future__ import annotations

from enum import Enum


class State(str, Enum):
    TICKET_DRAFT = "TICKET_DRAFT"
    TICKET_FROZEN = "TICKET_FROZEN"
    BUILDING = "BUILDING"
    STAGE_A_RUNNING = "STAGE_A_RUNNING"
    STAGE_A_PASS = "STAGE_A_PASS"
    STAGE_B_RUNNING = "STAGE_B_RUNNING"
    STAGE_B_PASS = "STAGE_B_PASS"
    COMMIT_PENDING = "COMMIT_PENDING"
    RATCHET = "RATCHET"
    DONE = "DONE"
    REWORK = "REWORK"
    PLATEAU_ESCALATE = "PLATEAU_ESCALATE"
    ABORTED_TAMPER = "ABORTED_TAMPER"


# Legal transitions. Anything not listed is a bug and raises in ``assert_transition``.
LEGAL: dict[State, frozenset[State]] = {
    State.TICKET_DRAFT: frozenset({State.TICKET_FROZEN}),
    State.TICKET_FROZEN: frozenset({State.BUILDING, State.ABORTED_TAMPER}),
    State.BUILDING: frozenset({State.STAGE_A_RUNNING, State.ABORTED_TAMPER}),
    State.STAGE_A_RUNNING: frozenset({State.STAGE_A_PASS, State.REWORK, State.ABORTED_TAMPER}),
    State.STAGE_A_PASS: frozenset({State.STAGE_B_RUNNING}),
    State.STAGE_B_RUNNING: frozenset({State.STAGE_B_PASS, State.REWORK, State.ABORTED_TAMPER}),
    # The single gateway edge. COMMIT_PENDING has exactly one predecessor.
    State.STAGE_B_PASS: frozenset({State.COMMIT_PENDING}),
    State.COMMIT_PENDING: frozenset({State.RATCHET, State.ABORTED_TAMPER}),
    State.RATCHET: frozenset({State.DONE}),
    State.REWORK: frozenset({State.BUILDING, State.PLATEAU_ESCALATE}),
    State.PLATEAU_ESCALATE: frozenset({State.BUILDING}),
    State.DONE: frozenset(),
    State.ABORTED_TAMPER: frozenset(),
}

# States that only the Gatekeeper may enter. The loop asserts it is not the mover here.
GATEKEEPER_ONLY_TARGETS: frozenset[State] = frozenset({State.COMMIT_PENDING, State.RATCHET, State.DONE})


class IllegalTransition(RuntimeError):
    pass


def assert_transition(src: State, dst: State) -> None:
    if dst not in LEGAL.get(src, frozenset()):
        raise IllegalTransition(f"illegal transition {src.value} -> {dst.value}")


def commit_pending_predecessors() -> frozenset[State]:
    """Introspection used by tests: which states can reach COMMIT_PENDING directly."""
    return frozenset(s for s, dsts in LEGAL.items() if State.COMMIT_PENDING in dsts)
