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
            ],
            behavior=[
                {"module": "bread_tick.py",
                 "call": "tick({'bakery_bread': 5, 'goose_bread': 3})['bakery_bread']", "expect": 6},
                {"module": "bread_tick.py", "call": "tick({'goose_bread': 0})['goose_bread']", "expect": 0},
            ]),
        Ticket(
            id="OP-3", title="placement.py: validate a building layout on the pond grid",
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="is_valid(cells, n) rejects out-of-bounds or "
                                    "overlapping placements", stage=Stage.B, rubric_ref="onepond/placement"),
            ],
            behavior=[
                {"module": "placement.py", "call": "is_valid([(0, 0), (1, 1)], 4)", "expect": True},
                {"module": "placement.py", "call": "is_valid([(0, 0), (0, 0)], 4)", "expect": False},
                {"module": "placement.py", "call": "is_valid([(5, 0)], 4)", "expect": False},
            ]),
        Ticket(
            id="OP-4",
            title=("pond_state.py: a One Pond simulation. A dict state holds 'bread' (int) and 'buildings' "
                   "(a list of dicts with 'kind','x','y'). step(state) returns the next state after one "
                   "tick: each 'bakery' adds (3 + number_of_granaries) bread (each 'granary' boosts every "
                   "bakery), each 'nest' subtracts 1, and bread never goes below 0. "
                   "add_building(state, kind, x, y, n) adds a building only if (x,y) is in-bounds on the "
                   "n-by-n grid and not already occupied, else returns the state unchanged. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="step ticks bread by building counts; add_building "
                                    "validates placement", stage=Stage.B, rubric_ref="onepond/state"),
            ],
            behavior=[
                {"module": "pond_state.py",
                 "call": "step({'bread': 0, 'buildings': [{'kind': 'bakery', 'x': 0, 'y': 0}]})['bread']",
                 "expect": 3},
                {"module": "pond_state.py",
                 "call": "step({'bread': 0, 'buildings': [{'kind':'bakery','x':0,'y':0},{'kind':'granary','x':1,'y':0}]})['bread']",
                 "expect": 4},
                {"module": "pond_state.py",
                 "call": "len(add_building({'bread': 0, 'buildings': []}, 'bakery', 9, 9, 4)['buildings'])",
                 "expect": 0},
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
            ],
            behavior=[
                {"module": "predator.py", "call": "is_safe([(0, 0)], [(0, 0)], 2)", "expect": True},
                {"module": "predator.py", "call": "is_safe([(9, 9)], [(0, 0)], 2)", "expect": False},
                {"module": "predator.py", "call": "is_safe([], [(0, 0)], 2)", "expect": True},
            ]),
        Ticket(
            id="OP-6",
            title=("pond_scene.py: bridge pond state to a renderable scene. build_body(buildings) takes a "
                   "list of dicts each {'kind': str, 'x': int, 'y': int} and returns a STRING of "
                   "newline-separated GDScript statements that, for each building, call "
                   "add_box(root, Vector3(1, 1, 1), COLOR, Vector3(x * 2, 0.5, y * 2)) where COLOR is "
                   "Color(0.5, 0.3, 0.1) for 'bakery', Color(0.8, 0.7, 0.4) for 'nest', "
                   "Color(0.5, 0.5, 0.5) for 'fence', Color(0.7, 0.5, 0.2) for 'granary', else Color.WHITE. "
                   "Pure Python returning a string; no Godot needed."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="returns the add_box statements joined by REAL newlines "
                                    "(chr 10) so each add_box is on its OWN line -- a literal backslash-n "
                                    "string is a BUG -- one statement per building with the right colour + "
                                    "grid position", stage=Stage.B, rubric_ref="onepond/scene"),
            ],
            behavior=[
                {"module": "pond_scene.py",
                 "call": "len([l for l in build_body([{'kind':'bakery','x':0,'y':0},{'kind':'nest','x':1,'y':1}]).split(chr(10)) if 'add_box' in l])",
                 "expect": 2},
                {"module": "pond_scene.py",
                 "call": "'0.7, 0.5, 0.2' in build_body([{'kind':'granary','x':0,'y':0}])", "expect": True},
                {"module": "pond_scene.py",
                 "call": "'0.5, 0.3, 0.1' in build_body([{'kind':'bakery','x':0,'y':0}])", "expect": True},
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
            ],
            behavior=[
                {"module": "granary.py", "call": "production(2, 1)", "expect": 8},
                {"module": "granary.py", "call": "production(4, 0)", "expect": 12},
                {"module": "granary.py", "call": "production(0, 5)", "expect": 0},
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
                AcceptanceCriterion(id="AC2", text="tick_bread must match kinds by the EXACT strings "
                                    "'bakery', 'granary', 'nest' (NOT 'baker') and return "
                                    "bakeries*(3+granaries) - nests. Concrete example that MUST hold: "
                                    "tick_bread([{'kind':'bakery'},{'kind':'bakery'},{'kind':'granary'},"
                                    "{'kind':'nest'}]) == 7", stage=Stage.B, rubric_ref="onepond/economy2"),
            ],
            behavior=[  # DETERMINISTIC gate (python_behavior) -- catches the 'baker' typo the reviewer missed
                {"module": "pond_economy.py",
                 "call": "tick_bread([{'kind':'bakery'},{'kind':'bakery'},{'kind':'granary'},{'kind':'nest'}])",
                 "expect": 7},
                {"module": "pond_economy.py", "call": "tick_bread([])", "expect": 0},
            ]),
        Ticket(
            id="OP-9",
            title=("pond_status.py: summarise a pond. pond_status(state, reach) returns a dict "
                   "{'bread': int, 'safe': bool} where 'bread' is state['bread'] and 'safe' is True iff "
                   "EVERY building of kind 'nest' in state['buildings'] is within Manhattan distance "
                   "`reach` (abs(dx)+abs(dy) <= reach) of at least one building of kind 'fence'. No nests "
                   "means safe. Buildings are dicts with 'kind','x','y'. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="'safe' true only when every nest is within reach of a "
                                    "fence; 'bread' passes through", stage=Stage.B, rubric_ref="onepond/status"),
            ],
            behavior=[
                {"module": "pond_status.py",
                 "call": "pond_status({'bread': 9, 'buildings': [{'kind':'nest','x':0,'y':0},{'kind':'fence','x':1,'y':0}]}, 2)['safe']",
                 "expect": True},
                {"module": "pond_status.py",
                 "call": "pond_status({'bread': 5, 'buildings': [{'kind':'nest','x':9,'y':9}]}, 2)['safe']",
                 "expect": False},
                {"module": "pond_status.py",
                 "call": "pond_status({'bread': 7, 'buildings': []}, 2)['bread']", "expect": 7},
            ]),
        Ticket(
            id="OP-10",
            title=("pond_outcome.py: evaluate the pond. pond_outcome(state, reach) returns a STRING: "
                   "'lost' if state['bread'] <= 0; otherwise 'unsafe' if any building of kind 'nest' is "
                   "NOT within Manhattan distance `reach` (abs(dx)+abs(dy) <= reach) of some building of "
                   "kind 'fence'; otherwise 'thriving'. No nests counts as safe. Buildings are dicts with "
                   "'kind','x','y'. Pure Python returning a str."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="returns 'lost' / 'unsafe' / 'thriving' per bread then "
                                    "predator safety", stage=Stage.B, rubric_ref="onepond/outcome"),
            ],
            behavior=[
                {"module": "pond_outcome.py", "call": "pond_outcome({'bread': 0, 'buildings': []}, 2)",
                 "expect": "lost"},
                {"module": "pond_outcome.py",
                 "call": "pond_outcome({'bread': 5, 'buildings': [{'kind':'nest','x':9,'y':9}]}, 2)",
                 "expect": "unsafe"},
                {"module": "pond_outcome.py",
                 "call": "pond_outcome({'bread': 5, 'buildings': [{'kind':'nest','x':0,'y':0},{'kind':'fence','x':1,'y':0}]}, 2)",
                 "expect": "thriving"},
                {"module": "pond_outcome.py", "call": "pond_outcome({'bread': 5, 'buildings': []}, 2)",
                 "expect": "thriving"},
            ]),
        Ticket(
            id="OP-11",
            title=("water_access.py: bakeries need water. has_water(buildings, reach) returns True iff "
                   "EVERY building of kind 'bakery' is within Manhattan distance `reach` "
                   "(abs(dx)+abs(dy) <= reach) of at least one building of kind 'well'. No bakeries means "
                   "True. Buildings are dicts with 'kind','x','y'. Pure Python returning a bool."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="True only when every bakery is within reach of a well",
                                    stage=Stage.B, rubric_ref="onepond/water"),
            ],
            behavior=[
                {"module": "water_access.py",
                 "call": "has_water([{'kind':'bakery','x':0,'y':0},{'kind':'well','x':1,'y':0}], 2)",
                 "expect": True},
                {"module": "water_access.py",
                 "call": "has_water([{'kind':'bakery','x':9,'y':9},{'kind':'well','x':0,'y':0}], 2)",
                 "expect": False},
                {"module": "water_access.py", "call": "has_water([], 2)", "expect": True},
                {"module": "water_access.py",
                 "call": "has_water([{'kind':'well','x':0,'y':0}], 2)", "expect": True},
            ]),
    ]
    for t in tickets:
        t.freeze()
    return tickets
