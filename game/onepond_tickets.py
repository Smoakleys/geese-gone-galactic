"""Authored One Pond tickets — the bounded jobs Claude writes for Icarus to build (Pond era only).

Per the plan, Claude authors the tickets + the gate; Icarus builds them through its agent runtime. This
is the game's first real backlog: each ticket has pre-committed acceptance criteria that a *certified*
Stage-A check (godot_parse / godot_render / python_syntax) or the Stage-B reviewer can judge. Feed these
to control.runner.AutonomousRunner with default_icarus_builder to drive One Pond forward.
"""

from __future__ import annotations

from harness.models import AcceptanceCriterion, Stage, Ticket, TicketKind


def one_pond_tickets() -> "list[Ticket]":
    """The authored One Pond backlog, frozen and ready to run."""
    tickets = [
        Ticket(
            id="OP-1", title="One Pond scene.gd: green land + a blue water pond + a building",
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible (non-blank) scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as an iso pond: land, water, and a building",
                                    stage=Stage.B, rubric_ref="onepond/scene"),
            ]),
        Ticket(
            id="OP-2", title="bread_tick.py: advance the pond bread economy by one tick",
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="a tick(state) that adds bakery bread and subtracts "
                                    "goose bread, returning the new state",
                                    stage=Stage.B, rubric_ref="onepond/economy"),
            ]),
        Ticket(
            id="OP-3", title="placement.py: validate a building layout on the pond grid",
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="is_valid(cells, n) rejects out-of-bounds or "
                                    "overlapping placements", stage=Stage.B, rubric_ref="onepond/placement"),
            ]),
    ]
    for t in tickets:
        t.freeze()
    return tickets
