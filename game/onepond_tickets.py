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
            # Templated (fast) scene ticket: routes to the fast resident model; default_icarus_builder's
            # post_build composes the content.gd into a full scene.gd before the Godot gates. ~90s vs ~20m.
            id="OP-1",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the provided "
                   "helpers add_plane(root, size, color, y=0.0) and add_box(root, size, color, pos). Build "
                   "the One Pond: a GREEN land plane size Vector2(16,16); a BLUE water pond size "
                   "Vector2(6,6) at y=0.1; and a brown add_box beside the pond. Do NOT add a Camera3D, "
                   "_ready(), your own meshes, or redefine the helpers -- just call them with "
                   "Color.GREEN/Color.BLUE (Godot 4)."),
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
        Ticket(
            id="OP-4",
            title=("pond_state.py: a One Pond simulation. A dict state holds 'bread' (int) and 'buildings' "
                   "(a list of dicts with 'kind','x','y'). step(state) returns the next state after one "
                   "tick: each 'bakery' adds 3 bread, each 'nest' subtracts 1 (bread never below 0). "
                   "add_building(state, kind, x, y, n) adds a building only if (x,y) is in-bounds on the "
                   "n-by-n grid and not already occupied, else returns the state unchanged. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="step ticks bread by building counts; add_building "
                                    "validates placement", stage=Stage.B, rubric_ref="onepond/state"),
            ]),
        Ticket(
            id="OP-5",
            title=("predator.py: a One Pond predator-safety rule. is_safe(nests, fences, reach) takes a "
                   "list of nest (x, y) tuples and a list of fence (x, y) tuples, and returns True only if "
                   "EVERY nest is within Manhattan distance `reach` (abs(dx)+abs(dy) <= reach) of at least "
                   "one fence. An empty nest list is safe. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="is_safe true only when every nest is within reach of a "
                                    "fence", stage=Stage.B, rubric_ref="onepond/predator"),
            ]),
        Ticket(
            id="OP-6",
            title=("pond_scene.py: bridge pond state to a renderable scene. build_body(buildings) takes a "
                   "list of dicts each {'kind': str, 'x': int, 'y': int} and returns a STRING of "
                   "newline-separated GDScript statements that, for each building, call "
                   "add_box(root, Vector3(1, 1, 1), COLOR, Vector3(x * 2, 0.5, y * 2)) where COLOR is "
                   "Color(0.5, 0.3, 0.1) for 'bakery', Color(0.8, 0.7, 0.4) for 'nest', "
                   "Color(0.5, 0.5, 0.5) for 'fence', else Color.WHITE. Pure Python returning a string; "
                   "no Godot needed."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="returns the add_box statements joined by REAL newlines "
                                    "(chr 10) so each add_box is on its OWN line -- a literal backslash-n "
                                    "string is a BUG -- one statement per building with the right colour + "
                                    "grid position", stage=Stage.B, rubric_ref="onepond/scene"),
            ]),
        Ticket(
            id="OP-7",
            title=("granary.py: a bakery-synergy building. production(bakeries, granaries) returns the "
                   "total bread produced per tick: each bakery makes a base of 3, and each granary adds "
                   "+1 to EVERY bakery, so the total is bakeries * (3 + granaries). With 0 bakeries the "
                   "total is 0 regardless of granaries. Pure Python, returns an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="production(b, g) == b * (3 + g), and 0 when b == 0",
                                    stage=Stage.B, rubric_ref="onepond/granary"),
            ]),
        Ticket(
            id="OP-8",
            title=("pond_economy.py: net bread per tick, using the granary synergy. tick_bread(buildings) "
                   "takes a list of building dicts each with a 'kind' key, counts the bakeries, granaries, "
                   "and nests, and returns the NET bread change for one tick: "
                   "bakeries * (3 + granaries) - nests. It may be negative. An empty list returns 0. "
                   "Pure Python, returns an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="tick_bread counts kinds and returns "
                                    "bakeries*(3+granaries) - nests", stage=Stage.B, rubric_ref="onepond/economy2"),
            ]),
    ]
    for t in tickets:
        t.freeze()
    return tickets
