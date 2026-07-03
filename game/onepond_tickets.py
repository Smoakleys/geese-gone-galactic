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
                   "Color(0.5, 0.5, 0.5) for 'fence', Color(0.7, 0.5, 0.2) for 'granary', "
                   "Color(0.2, 0.4, 0.8) for 'well', else Color.WHITE. "
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
                {"module": "pond_scene.py",
                 "call": "'0.2, 0.4, 0.8' in build_body([{'kind':'well','x':0,'y':0}])", "expect": True},
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
            title=("pond_outcome.py: evaluate the pond. pond_outcome(state, reach) returns a STRING, "
                   "checked IN THIS ORDER: 'lost' if state['bread'] <= 0; otherwise 'dry' if any building "
                   "of kind 'bakery' is NOT within Manhattan distance `reach` (abs(dx)+abs(dy) <= reach) "
                   "of some building of kind 'well'; otherwise 'unsafe' if any building of kind 'nest' is "
                   "NOT within `reach` of some building of kind 'fence'; otherwise 'thriving'. No bakeries "
                   "counts as watered; no nests counts as safe. Buildings are dicts with 'kind','x','y'. "
                   "Pure Python returning a str."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="returns 'lost' / 'dry' / 'unsafe' / 'thriving' per "
                                    "bread, then water access, then predator safety",
                                    stage=Stage.B, rubric_ref="onepond/outcome"),
            ],
            behavior=[
                {"module": "pond_outcome.py", "call": "pond_outcome({'bread': 0, 'buildings': []}, 2)",
                 "expect": "lost"},
                {"module": "pond_outcome.py",
                 "call": "pond_outcome({'bread': 5, 'buildings': [{'kind':'bakery','x':0,'y':0}]}, 2)",
                 "expect": "dry"},
                {"module": "pond_outcome.py",
                 "call": "pond_outcome({'bread': 5, 'buildings': [{'kind':'nest','x':9,'y':9}]}, 2)",
                 "expect": "unsafe"},
                {"module": "pond_outcome.py",
                 "call": "pond_outcome({'bread': 5, 'buildings': [{'kind':'bakery','x':0,'y':0},{'kind':'well','x':1,'y':0}]}, 2)",
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
        Ticket(
            id="OP-12",
            title=("pond_score.py: a net-worth score for the pond. pond_score(state) returns an int = "
                   "state['bread'] plus, for each building in state['buildings'], 10 for a 'bakery', 5 for "
                   "a 'granary', 3 for a 'nest', and 2 for any other kind. Buildings are dicts with a "
                   "'kind'. Pure Python returning an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="bread plus weighted building values "
                                    "(bakery 10, granary 5, nest 3, else 2)",
                                    stage=Stage.B, rubric_ref="onepond/score"),
            ],
            behavior=[
                {"module": "pond_score.py", "call": "pond_score({'bread': 5, 'buildings': []})",
                 "expect": 5},
                {"module": "pond_score.py",
                 "call": "pond_score({'bread': 0, 'buildings': [{'kind':'bakery'}]})", "expect": 10},
                {"module": "pond_score.py",
                 "call": "pond_score({'bread': 10, 'buildings': [{'kind':'bakery'},{'kind':'granary'},{'kind':'nest'}]})",
                 "expect": 28},
                {"module": "pond_score.py",
                 "call": "pond_score({'bread': 1, 'buildings': [{'kind':'well'}]})", "expect": 3},
            ]),
        Ticket(
            id="OP-13",
            title=("pond_advice.py: a hint system. pond_advice(state, reach) inspects state['buildings'] "
                   "(dicts with 'kind','x','y') and returns a SHORT advice STRING for the weakest point, "
                   "checked IN THIS ORDER: 'build a bakery' if there is no 'bakery' at all; otherwise "
                   "'build a well' if any 'bakery' is NOT within Manhattan distance `reach` of a 'well'; "
                   "otherwise 'build a fence' if any 'nest' is NOT within `reach` of a 'fence'; otherwise "
                   "'looking good'. Pure Python returning a str."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="suggests bakery -> well -> fence -> 'looking good' by "
                                    "the pond's weakest point", stage=Stage.B, rubric_ref="onepond/advice"),
            ],
            behavior=[
                {"module": "pond_advice.py", "call": "pond_advice({'buildings': []}, 2)",
                 "expect": "build a bakery"},
                {"module": "pond_advice.py",
                 "call": "pond_advice({'buildings': [{'kind':'bakery','x':0,'y':0}]}, 2)",
                 "expect": "build a well"},
                {"module": "pond_advice.py",
                 "call": "pond_advice({'buildings': [{'kind':'bakery','x':0,'y':0},{'kind':'well','x':1,'y':0},{'kind':'nest','x':5,'y':5}]}, 2)",
                 "expect": "build a fence"},
                {"module": "pond_advice.py",
                 "call": "pond_advice({'buildings': [{'kind':'bakery','x':0,'y':0},{'kind':'well','x':1,'y':0}]}, 2)",
                 "expect": "looking good"},
            ]),
        Ticket(
            id="OP-14",
            title=("predator_loss.py: predators have teeth. predator_loss(state, reach) reads "
                   "state['buildings'] (a list of dicts with 'kind','x','y') and returns the int bread "
                   "eaten by predators this tick: 2 for EACH building of kind 'nest' that is NOT within "
                   "Manhattan distance `reach` (abs(dx)+abs(dy) <= reach) of any building of kind 'fence'. "
                   "A guarded nest loses nothing. NOTE: state is a DICT with a 'buildings' key, not a bare "
                   "list. Pure Python returning an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="2 bread per UNGUARDED nest; guarded nests lose nothing",
                                    stage=Stage.B, rubric_ref="onepond/predloss"),
            ],
            behavior=[
                {"module": "predator_loss.py",
                 "call": "predator_loss({'buildings': [{'kind':'nest','x':0,'y':0}]}, 2)", "expect": 2},
                {"module": "predator_loss.py",
                 "call": "predator_loss({'buildings': [{'kind':'nest','x':0,'y':0},{'kind':'fence','x':1,'y':0}]}, 2)",
                 "expect": 0},
                {"module": "predator_loss.py",
                 "call": "predator_loss({'buildings': [{'kind':'nest','x':0,'y':0},{'kind':'nest','x':9,'y':9},{'kind':'fence','x':1,'y':0}]}, 2)",
                 "expect": 2},
                {"module": "predator_loss.py", "call": "predator_loss({'buildings': []}, 2)", "expect": 0},
            ]),
        Ticket(
            id="OP-15",
            title=("build_cost.py: buildings cost bread. total_cost(buildings) returns the int total bread "
                   "cost to place them, summing per building by kind: 'bakery' 5, 'granary' 4, 'well' 3, "
                   "'fence' 2, 'nest' 1, and 0 for any unknown kind. Buildings are dicts with a 'kind'. "
                   "Pure Python returning an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="sums per-kind costs (bakery 5/granary 4/well 3/fence "
                                    "2/nest 1/else 0)", stage=Stage.B, rubric_ref="onepond/cost"),
            ],
            behavior=[
                {"module": "build_cost.py",
                 "call": "total_cost([{'kind':'bakery'},{'kind':'nest'}])", "expect": 6},
                {"module": "build_cost.py", "call": "total_cost([{'kind':'well'},{'kind':'well'}])",
                 "expect": 6},
                {"module": "build_cost.py", "call": "total_cost([])", "expect": 0},
                {"module": "build_cost.py", "call": "total_cost([{'kind':'rocket'}])", "expect": 0},
            ]),
        Ticket(
            id="OP-16",
            title=("pond_rank.py: pond progression. pond_rank(score) returns the pond's rank as a STRING "
                   "by its score: 'hamlet' if score < 20; 'village' if score < 50; 'town' if score < 100; "
                   "otherwise 'city'. (Boundaries belong to the higher tier: 20 -> village, 50 -> town, "
                   "100 -> city.) Pure Python returning a str."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="hamlet<20 / village<50 / town<100 / city>=100, "
                                    "boundaries to the higher tier", stage=Stage.B, rubric_ref="onepond/rank"),
            ],
            behavior=[
                {"module": "pond_rank.py", "call": "pond_rank(10)", "expect": "hamlet"},
                {"module": "pond_rank.py", "call": "pond_rank(20)", "expect": "village"},
                {"module": "pond_rank.py", "call": "pond_rank(75)", "expect": "town"},
                {"module": "pond_rank.py", "call": "pond_rank(100)", "expect": "city"},
            ]),
        Ticket(
            id="OP-17",
            title=("goose_count.py: how many geese live in the pond. goose_count(buildings) returns the "
                   "int goose population: each building of kind 'nest' houses 4 geese; all other kinds "
                   "house none. Buildings are dicts with a 'kind'. Pure Python returning an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="4 geese per nest, 0 for other kinds",
                                    stage=Stage.B, rubric_ref="onepond/geese"),
            ],
            behavior=[
                {"module": "goose_count.py",
                 "call": "goose_count([{'kind':'nest'},{'kind':'nest'}])", "expect": 8},
                {"module": "goose_count.py",
                 "call": "goose_count([{'kind':'nest'},{'kind':'bakery'}])", "expect": 4},
                {"module": "goose_count.py", "call": "goose_count([])", "expect": 0},
                {"module": "goose_count.py", "call": "goose_count([{'kind':'bakery'}])", "expect": 0},
            ]),
        Ticket(
            id="OP-18",
            title=("pond_report.py: a one-line status line. report(bread, rank, safe) returns EXACTLY the "
                   "string \"Pond: {bread} bread, rank {rank}, {status}\" where {bread} is the int, {rank} "
                   "is the rank string, and {status} is 'safe' when safe is True else 'in danger'. Example: "
                   "report(14, 'village', True) -> 'Pond: 14 bread, rank village, safe'. Pure Python "
                   "returning a str; match the format EXACTLY (spaces, commas, wording)."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="exact format 'Pond: {bread} bread, rank {rank}, "
                                    "{safe|in danger}'", stage=Stage.B, rubric_ref="onepond/report"),
            ],
            behavior=[
                {"module": "pond_report.py", "call": "report(14, 'village', True)",
                 "expect": "Pond: 14 bread, rank village, safe"},
                {"module": "pond_report.py", "call": "report(0, 'hamlet', False)",
                 "expect": "Pond: 0 bread, rank hamlet, in danger"},
                {"module": "pond_report.py", "call": "report(100, 'city', True)",
                 "expect": "Pond: 100 bread, rank city, safe"},
            ]),
        Ticket(
            id="OP-19",
            title=("nearest_fence.py: find the closest fence to a nest. nearest_fence(nest, fences) takes "
                   "a nest (x, y) tuple and a list of fence (x, y) tuples, and returns the fence tuple with "
                   "the SMALLEST Manhattan distance (abs(dx)+abs(dy)) to the nest. On a tie, return the "
                   "EARLIEST such fence in the list. Return None if the fence list is empty. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="returns the min-Manhattan-distance fence (earliest on "
                                    "tie), or None if empty", stage=Stage.B, rubric_ref="onepond/nearest"),
            ],
            behavior=[
                {"module": "nearest_fence.py", "call": "nearest_fence((0, 0), [(3, 0), (0, 2)])",
                 "expect": (0, 2)},
                {"module": "nearest_fence.py", "call": "nearest_fence((5, 5), [(5, 4), (0, 0)])",
                 "expect": (5, 4)},
                {"module": "nearest_fence.py", "call": "nearest_fence((0, 0), [(1, 0), (0, 1)])",
                 "expect": (1, 0)},
                {"module": "nearest_fence.py", "call": "nearest_fence((0, 0), [])", "expect": None},
            ]),
        Ticket(
            id="OP-20",
            title=("count_by_kind.py: a building inventory. count_by_kind(buildings) takes a list of dicts "
                   "each with a 'kind' and returns a DICT mapping each kind present to how many there are. "
                   "Kinds with zero are absent from the dict; an empty list returns an empty dict {}. "
                   "Pure Python returning a dict."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="dict of kind -> count; empty list -> {}",
                                    stage=Stage.B, rubric_ref="onepond/inventory"),
            ],
            behavior=[
                {"module": "count_by_kind.py",
                 "call": "count_by_kind([{'kind':'bakery'},{'kind':'bakery'},{'kind':'nest'}])",
                 "expect": {"bakery": 2, "nest": 1}},
                {"module": "count_by_kind.py", "call": "count_by_kind([])", "expect": {}},
                {"module": "count_by_kind.py", "call": "count_by_kind([{'kind':'well'}])",
                 "expect": {"well": 1}},
            ]),
        Ticket(
            id="OP-21",
            title=("sorted_by_distance.py: order cells by nearness. sorted_by_distance(cells, point) takes "
                   "a list of (x, y) cell tuples and a point (x, y), and returns a NEW list of the cells "
                   "sorted ASCENDING by Manhattan distance (abs(dx)+abs(dy)) to the point. Ties keep their "
                   "original relative order (stable). An empty list returns []. Pure Python returning a list."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="ascending by Manhattan distance, stable on ties",
                                    stage=Stage.B, rubric_ref="onepond/sortdist"),
            ],
            behavior=[
                {"module": "sorted_by_distance.py",
                 "call": "sorted_by_distance([(5, 5), (1, 0), (0, 2)], (0, 0))",
                 "expect": [(1, 0), (0, 2), (5, 5)]},
                {"module": "sorted_by_distance.py",
                 "call": "sorted_by_distance([(0, 1), (1, 0)], (0, 0))", "expect": [(0, 1), (1, 0)]},
                {"module": "sorted_by_distance.py", "call": "sorted_by_distance([], (0, 0))", "expect": []},
            ]),
        Ticket(
            id="OP-22",
            title=("simulate_bread.py: project the bread economy. simulate_bread(start, bakeries, nests, "
                   "ticks) simulates `ticks` ticks starting from `start` bread. EACH tick: add bakeries*3, "
                   "subtract nests, then CLAMP to >= 0 (bread never goes negative, and clamping happens "
                   "every tick so a formula won't do). Return the final bread as an int. Pure Python."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="iterate ticks, +bakeries*3 -nests, clamp >=0 each tick",
                                    stage=Stage.B, rubric_ref="onepond/simulate"),
            ],
            behavior=[
                {"module": "simulate_bread.py", "call": "simulate_bread(10, 2, 1, 3)", "expect": 25},
                {"module": "simulate_bread.py", "call": "simulate_bread(2, 0, 1, 5)", "expect": 0},
                {"module": "simulate_bread.py", "call": "simulate_bread(5, 1, 0, 2)", "expect": 11},
            ]),
        Ticket(
            id="OP-23",
            title=("unique_kinds.py: distinct building kinds. unique_kinds(buildings) takes a list of dicts "
                   "each with a 'kind' and returns a SORTED list of the DISTINCT kinds present (each kind "
                   "once, alphabetical order). An empty list returns []. Pure Python returning a list."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="distinct kinds, sorted alphabetically",
                                    stage=Stage.B, rubric_ref="onepond/uniquekinds"),
            ],
            behavior=[
                {"module": "unique_kinds.py",
                 "call": "unique_kinds([{'kind':'nest'},{'kind':'bakery'},{'kind':'nest'}])",
                 "expect": ["bakery", "nest"]},
                {"module": "unique_kinds.py", "call": "unique_kinds([])", "expect": []},
                {"module": "unique_kinds.py",
                 "call": "unique_kinds([{'kind':'well'},{'kind':'well'}])", "expect": ["well"]},
            ]),
        Ticket(
            # Templated (fast) scene ticket, like OP-1: routes to the fast model; post_build materialises
            # content.gd into a full scene.gd before the Godot gates. Advances the thin visual game -- a goose!
            id="OP-24",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0) and add_box(root, size, color, pos). Build a One "
                   "Pond WITH A GOOSE: a GREEN land plane Vector2(16, 16); a BLUE pond Vector2(6, 6) at "
                   "y=0.1; and a goose beside the pond made of add_box calls -- a WHITE body box about "
                   "Vector3(1.2, 0.8, 2), a WHITE head box Vector3(0.6, 0.8, 0.6) sitting above the front "
                   "of the body, and a small ORANGE beak box using Color(1, 0.5, 0). Use Color.GREEN, "
                   "Color.BLUE, Color.WHITE (Godot 4). Do NOT add a Camera3D, _ready(), your own meshes, "
                   "or redefine the helpers -- just call them."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible (non-blank) scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as an iso pond with a white goose beside it",
                                    stage=Stage.B, rubric_ref="onepond/goose"),
            ]),
        Ticket(
            id="OP-25",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0) and add_box(root, size, color, pos). Build One "
                   "Pond with a FLOCK of geese: a GREEN land plane Vector2(16, 16); a BLUE pond "
                   "Vector2(6, 6) at y=0.1; and THREE white geese at DIFFERENT spots beside the pond. Each "
                   "goose is a WHITE body box about Vector3(1, 0.7, 1.6) + a WHITE head box Vector3(0.5, "
                   "0.7, 0.5) above the front of that body + a small ORANGE beak box Color(1, 0.5, 0). "
                   "Space the three geese apart. Use Color.GREEN/Color.BLUE/Color.WHITE (Godot 4). No "
                   "Camera3D, no _ready(), don't redefine the helpers."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible (non-blank) scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as an iso pond with a flock of white geese",
                                    stage=Stage.B, rubric_ref="onepond/flock"),
            ]),
        Ticket(
            id="OP-26",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0) and add_box(root, size, color, pos). Build the "
                   "COMPLETE One Pond world: a GREEN land plane Vector2(16, 16); a BLUE pond Vector2(6, 6) "
                   "at y=0.1; a BROWN bakery box Color(0.5, 0.3, 0.1) size Vector3(1.5, 1.5, 1.5); a TAN "
                   "nest box Color(0.8, 0.7, 0.4) size Vector3(1, 0.6, 1); and TWO white geese near the "
                   "pond (each a WHITE body box Vector3(1, 0.7, 1.6) + a WHITE head box Vector3(0.5, 0.7, "
                   "0.5) above its front + an ORANGE beak box Color(1, 0.5, 0)). Space everything apart. "
                   "Use Color.GREEN/Color.BLUE/Color.WHITE (Godot 4). No Camera3D, no _ready(), don't "
                   "redefine the helpers."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible (non-blank) scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as a pond with buildings and geese",
                                    stage=Stage.B, rubric_ref="onepond/world"),
            ]),
        Ticket(
            id="OP-27",
            title=("affordable_buildings.py: what can I build? affordable_buildings(bread) returns the "
                   "SORTED (alphabetical) list of building kinds whose bread cost is <= `bread`, where the "
                   "costs are bakery 5, granary 4, well 3, fence 2, nest 1. An empty result is []. Pure "
                   "Python returning a list of strings."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="sorted kinds affordable at `bread` (bakery 5/granary "
                                    "4/well 3/fence 2/nest 1)", stage=Stage.B, rubric_ref="onepond/afford"),
            ],
            behavior=[
                {"module": "affordable_buildings.py", "call": "affordable_buildings(4)",
                 "expect": ["fence", "granary", "nest", "well"]},
                {"module": "affordable_buildings.py", "call": "affordable_buildings(1)", "expect": ["nest"]},
                {"module": "affordable_buildings.py", "call": "affordable_buildings(0)", "expect": []},
                {"module": "affordable_buildings.py", "call": "affordable_buildings(5)",
                 "expect": ["bakery", "fence", "granary", "nest", "well"]},
            ]),
        Ticket(
            id="OP-28",
            title=("pond_event.py: random pond events. apply_event(state, event) returns a NEW state (do "
                   "not mutate the input) after applying the named event to state['bread']: 'harvest' adds "
                   "10, 'fox' subtracts 5, 'flood' halves it (integer floor division // 2), and any other "
                   "event leaves bread unchanged. Bread never goes below 0. Keep state['buildings'] "
                   "unchanged. Pure Python returning a dict."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="harvest +10 / fox -5 / flood //2 / else unchanged, "
                                    "clamp >=0, new state", stage=Stage.B, rubric_ref="onepond/event"),
            ],
            behavior=[
                {"module": "pond_event.py",
                 "call": "apply_event({'bread': 10, 'buildings': []}, 'harvest')['bread']", "expect": 20},
                {"module": "pond_event.py",
                 "call": "apply_event({'bread': 3, 'buildings': []}, 'fox')['bread']", "expect": 0},
                {"module": "pond_event.py",
                 "call": "apply_event({'bread': 11, 'buildings': []}, 'flood')['bread']", "expect": 5},
                {"module": "pond_event.py",
                 "call": "apply_event({'bread': 8, 'buildings': []}, 'calm')['bread']", "expect": 8},
            ]),
        Ticket(
            id="OP-29",
            title=("parse_command.py: parse a player text command. parse_command(text) splits `text` on "
                   "whitespace and returns a 2-tuple (verb, target): the FIRST word lowercased as the verb "
                   "and the SECOND word lowercased as the target (extra words ignored). If there is no "
                   "second word the target is '' (empty string); an empty/blank string returns ('', ''). "
                   "Pure Python returning a tuple of two strings."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="(verb, target) lowercased from the first two words, "
                                    "'' for missing", stage=Stage.B, rubric_ref="onepond/parse"),
            ],
            behavior=[
                {"module": "parse_command.py", "call": "parse_command('Build Bakery')",
                 "expect": ("build", "bakery")},
                {"module": "parse_command.py", "call": "parse_command('place well now')",
                 "expect": ("place", "well")},
                {"module": "parse_command.py", "call": "parse_command('quit')", "expect": ("quit", "")},
                {"module": "parse_command.py", "call": "parse_command('   ')", "expect": ("", "")},
            ]),
        Ticket(
            id="OP-30",
            title=("serialize_pond.py: save a pond to a compact string. serialize_pond(state) returns "
                   "EXACTLY \"bread={bread}\" followed, for each building in state['buildings'] IN ORDER, "
                   "by \";{kind}@{x},{y}\". So a pond with bread 10 and a bakery at (0,0) serialises to "
                   "'bread=10;bakery@0,0'. An empty buildings list gives just 'bread={bread}'. Match the "
                   "format EXACTLY (the '@' and the comma). Pure Python returning a str."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="exact 'bread=N' then ';kind@x,y' per building",
                                    stage=Stage.B, rubric_ref="onepond/serialize"),
            ],
            behavior=[
                {"module": "serialize_pond.py",
                 "call": "serialize_pond({'bread': 10, 'buildings': [{'kind':'bakery','x':0,'y':0}]})",
                 "expect": "bread=10;bakery@0,0"},
                {"module": "serialize_pond.py",
                 "call": "serialize_pond({'bread': 5, 'buildings': []})", "expect": "bread=5"},
                {"module": "serialize_pond.py",
                 "call": "serialize_pond({'bread': 0, 'buildings': [{'kind':'nest','x':2,'y':3},{'kind':'well','x':1,'y':0}]})",
                 "expect": "bread=0;nest@2,3;well@1,0"},
            ]),
        Ticket(
            id="OP-31",
            title=("deserialize_pond.py: load a pond from a string (the inverse of serialize_pond). "
                   "deserialize_pond(text) parses \"bread={N}\" optionally followed by \";{kind}@{x},{y}\" "
                   "parts (semicolon-separated) and returns the state dict {'bread': int, 'buildings': "
                   "[{'kind': str, 'x': int, 'y': int}, ...]} in order. 'bread=5' gives an empty buildings "
                   "list. x and y are ints. Pure Python returning a dict."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="parses 'bread=N;kind@x,y' back into the state dict",
                                    stage=Stage.B, rubric_ref="onepond/deserialize"),
            ],
            behavior=[
                {"module": "deserialize_pond.py",
                 "call": "deserialize_pond('bread=10;bakery@0,0')",
                 "expect": {"bread": 10, "buildings": [{"kind": "bakery", "x": 0, "y": 0}]}},
                {"module": "deserialize_pond.py", "call": "deserialize_pond('bread=5')",
                 "expect": {"bread": 5, "buildings": []}},
                {"module": "deserialize_pond.py",
                 "call": "deserialize_pond('bread=0;nest@2,3;well@1,0')['buildings'][1]",
                 "expect": {"kind": "well", "x": 1, "y": 0}},
            ]),
        Ticket(
            id="OP-32",
            title=("optimal_bakeries.py: plan production. Each bakery makes (3 + granaries) bread per tick. "
                   "optimal_bakeries(target, granaries) returns the MINIMUM number of bakeries needed so "
                   "the total bread per tick is >= `target` -- i.e. ceil(target / (3 + granaries)). If "
                   "target <= 0 return 0. Use integer math (no float rounding errors). Pure Python "
                   "returning an int."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="valid python (parses)",
                                    stage=Stage.A, check_hint="python_syntax"),
                AcceptanceCriterion(id="AC2", text="ceil(target / (3+granaries)) bakeries, 0 if target<=0",
                                    stage=Stage.B, rubric_ref="onepond/optimal"),
            ],
            behavior=[
                {"module": "optimal_bakeries.py", "call": "optimal_bakeries(10, 0)", "expect": 4},
                {"module": "optimal_bakeries.py", "call": "optimal_bakeries(8, 1)", "expect": 2},
                {"module": "optimal_bakeries.py", "call": "optimal_bakeries(9, 0)", "expect": 3},
                {"module": "optimal_bakeries.py", "call": "optimal_bakeries(0, 0)", "expect": 0},
            ]),
        Ticket(
            id="OP-34",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0), add_box(root, size, color, pos), and "
                   "add_sphere(root, radius, color, pos). Build One Pond with a MORE DETAILED, recognisable "
                   "low-poly goose (compose several primitives so it reads as a goose, not a blob): a GREEN "
                   "land plane Vector2(16, 16); a BLUE pond Vector2(6, 6) at y=0.1; and a goose near the "
                   "pond made of -- a large WHITE sphere BODY (radius ~0.9) at about y=0.9; a CURVED NECK of "
                   "TWO smaller WHITE spheres (radius ~0.3) stepping UP and FORWARD from the front-top of "
                   "the body; a WHITE sphere HEAD (radius ~0.4) on top of the neck; a small ORANGE beak box "
                   "Color(1, 0.5, 0) at the FRONT of the head; and a WHITE box TAIL (about Vector3(0.5, "
                   "0.3, 0.4)) at the BACK of the body, raised slightly. Keep the goose pieces close "
                   "together so they connect. Use Color.GREEN/Color.BLUE/Color.WHITE (Godot 4). No "
                   "Camera3D, no _ready(), don't redefine the helpers."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible multi-element scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as a pond with a detailed white goose",
                                    stage=Stage.B, rubric_ref="onepond/detailgoose"),
            ]),
        Ticket(
            id="OP-35",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0), add_box(root, size, color, pos), and "
                   "add_sphere(root, radius, color, pos). POSITION everything with the pos/y ARGUMENTS only "
                   "-- do NOT set .position or .translation on the returned node. Build the COMPLETE One "
                   "Pond WORLD with a DETAILED goose: a GREEN land plane Vector2(16, 16); a BLUE pond "
                   "Vector2(6, 6) at y=0.1; a BROWN bakery box Color(0.5, 0.3, 0.1) size Vector3(1.5, 1.5, "
                   "1.5) at about Vector3(5, 0.75, 5); a TAN nest box Color(0.8, 0.7, 0.4) size Vector3(1, "
                   "0.6, 1) at about Vector3(-5, 0.3, 5); and a detailed goose near the pond made of a WHITE "
                   "sphere BODY (radius ~0.8) at about Vector3(-2, 0.8, -2), a CURVED NECK of TWO smaller "
                   "WHITE spheres (radius ~0.3) stepping up and forward, a WHITE sphere HEAD (radius ~0.4), "
                   "an ORANGE beak box Color(1, 0.5, 0) at the head front, and a WHITE box TAIL at the body "
                   "back. Use Color.GREEN/Color.BLUE/Color.WHITE (Godot 4). No Camera3D, no _ready(), don't "
                   "redefine the helpers."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible multi-element scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as the pond world with buildings and a detailed goose",
                                    stage=Stage.B, rubric_ref="onepond/detailworld"),
            ]),
        Ticket(
            id="OP-36",
            title=("Write content.gd with ONLY `func build(root: Node3D) -> void:` using the helpers "
                   "add_plane(root, size, color, y=0.0), add_box(root, size, color, pos), and "
                   "add_sphere(root, radius, color, pos). POSITION everything with the pos/y ARGUMENTS only "
                   "(do NOT set .position/.translation). Build One Pond with a DETAILED FLOCK: a GREEN land "
                   "plane Vector2(16, 16); a BLUE pond Vector2(6, 6) at y=0.1; and TWO detailed geese at "
                   "DIFFERENT spots beside the pond. Each goose = a WHITE sphere BODY (radius ~0.7), a "
                   "CURVED NECK of TWO smaller WHITE spheres (radius ~0.25) stepping up and forward, a WHITE "
                   "sphere HEAD (radius ~0.35), and an ORANGE beak box Color(1, 0.5, 0) at the head front. "
                   "Space the two geese apart. Use Color.GREEN/Color.BLUE/Color.WHITE (Godot 4). No "
                   "Camera3D, no _ready(), don't redefine the helpers."),
            kind=TicketKind.SYSTEM,
            acceptance_criteria=[
                AcceptanceCriterion(id="AC1", text="scene.gd parses under godot --check-only",
                                    stage=Stage.A, check_hint="godot_parse"),
                AcceptanceCriterion(id="AC2", text="renders a visible multi-element scene",
                                    stage=Stage.A, check_hint="godot_render"),
                AcceptanceCriterion(id="AC3", text="reads as a pond with a flock of detailed geese",
                                    stage=Stage.B, rubric_ref="onepond/detailflock"),
            ]),
    ]
    for t in tickets:
        t.freeze()
    return tickets
