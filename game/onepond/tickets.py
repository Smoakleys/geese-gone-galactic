"""The One Pond ticket set + the Icarus generation client that satisfies it.

These are the real work items Phase 4 drives through the harness to prove the loop end-to-end:
each ticket has acceptance criteria frozen before the build, produces a ``onepond_config.json``
artifact, and must clear Stage A (placement legal + economy solvent + valid JSON) and Stage B
(reviewer) before the Gatekeeper commits it. The progression bakery → +hatchery → +granary is
the smallest sequence that exercises a producer, a consumer, and storage while staying solvent.

``onepond_generation_client`` is a scripted stand-in for Icarus that emits a correct config per
ticket — enough to demonstrate full autonomy. Swapping it for a real ``GenerationClient`` (a
local model) is the only change needed to make this a real Icarus build.
"""

from __future__ import annotations

import json

from harness.icarus.llm_builder import ScriptedGenerationClient
from harness.models import AcceptanceCriterion, Stage, Ticket, TicketKind

# Target pond for each ticket: a strictly-growing, always-solvent layout.
POND_CONFIGS: dict[str, dict] = {
    "T-POND-01": {
        "grid": [8, 8], "start_bread": 12,
        "buildings": [{"type": "bakery", "x": 1, "y": 1}],
    },
    "T-POND-02": {
        "grid": [8, 8], "start_bread": 12,
        "buildings": [
            {"type": "bakery", "x": 1, "y": 1},
            {"type": "bakery", "x": 2, "y": 1},
            {"type": "hatchery", "x": 3, "y": 1},
        ],
    },
    "T-POND-03": {
        "grid": [8, 8], "start_bread": 14,
        "buildings": [
            {"type": "bakery", "x": 1, "y": 1},
            {"type": "bakery", "x": 2, "y": 1},
            {"type": "hatchery", "x": 3, "y": 1},
            {"type": "granary", "x": 4, "y": 1},
        ],
    },
    "T-POND-04": {
        "grid": [8, 8], "start_bread": 16,
        "buildings": [
            {"type": "bakery", "x": 1, "y": 1},
            {"type": "bakery", "x": 2, "y": 1},
            {"type": "hatchery", "x": 3, "y": 1},
            {"type": "granary", "x": 4, "y": 1},
            {"type": "launchpad", "x": 5, "y": 1},
        ],
    },
    "T-POND-05": {
        # The complete galactic sanctuary: foxes prowl the pond, so the flock must be fenced
        # while it still launches. Two fences neutralize the two predators; the pond stays
        # solvent, keeps a living flock, and sends geese galactic.
        "grid": [8, 8], "start_bread": 20, "predators": 2,
        "buildings": [
            {"type": "bakery", "x": 1, "y": 1},
            {"type": "bakery", "x": 2, "y": 1},
            {"type": "hatchery", "x": 3, "y": 1},
            {"type": "granary", "x": 4, "y": 1},
            {"type": "launchpad", "x": 5, "y": 1},
            {"type": "fence", "x": 1, "y": 2},
            {"type": "fence", "x": 2, "y": 2},
        ],
    },
    "T-POND-06": {
        # The whole pond: every building type at once. Adds a well that waters the hatchery
        # (placed one tile away) on top of the fenced, launching, solvent sanctuary.
        "grid": [8, 8], "start_bread": 26, "predators": 2,
        "buildings": [
            {"type": "bakery", "x": 1, "y": 1},
            {"type": "bakery", "x": 2, "y": 1},
            {"type": "hatchery", "x": 3, "y": 1},
            {"type": "granary", "x": 4, "y": 1},
            {"type": "launchpad", "x": 5, "y": 1},
            {"type": "fence", "x": 1, "y": 2},
            {"type": "fence", "x": 2, "y": 2},
            {"type": "well", "x": 3, "y": 2},
        ],
    },
}

_TITLES = {
    "T-POND-01": "Place the first bakery (bread producer)",
    "T-POND-02": "Add a hatchery that hatches geese without bankrupting the pond",
    "T-POND-03": "Add a granary; a complete, solvent One Pond",
    "T-POND-04": "Add a launchpad; send the geese galactic while staying solvent",
    "T-POND-05": "Fence out the foxes; a galactic sanctuary that keeps its flock alive",
    "T-POND-06": "Sink a well; water the flock in the complete pond (every building type)",
}

# Tickets that must also send geese to space earn a launch-viability acceptance criterion.
_LAUNCH_TICKETS = {"T-POND-04", "T-POND-05", "T-POND-06"}
# Ponds that invest in a granary (goose capacity) must keep a living flock — the harvested
# liveliness gate. These are exactly the tickets that build a granary.
_LIVELINESS_TICKETS = {"T-POND-03", "T-POND-04", "T-POND-05", "T-POND-06"}
# Ponds that let predators in must fence the flock — the harvested predator-safety gate.
_PREDATOR_TICKETS = {"T-POND-05", "T-POND-06"}
# Ponds that sink a well must water their hatcheries — the water-access gate.
_WATER_TICKETS = {"T-POND-06"}


def _ticket(tid: str) -> Ticket:
    criteria = [
        AcceptanceCriterion(
            id="AC1", text="onepond_config.json places all buildings legally and stays "
                            "bread-solvent for 20 ticks", stage=Stage.A,
            check_hint="onepond_economy_solvent"),
        AcceptanceCriterion(
            id="AC2", text="reads as a functioning pond: a bread producer feeds the geese "
                            "economy without going bankrupt", stage=Stage.B,
            rubric_ref="game/onepond/rubric.md"),
    ]
    if tid in _LIVELINESS_TICKETS:
        criteria.append(AcceptanceCriterion(
            id="AC_LIVE", text="not a dead pond: the granary's goose capacity is backed by a "
                               "living flock — at least one goose is hatched within 20 ticks",
            stage=Stage.A, check_hint="onepond_liveliness"))
    if tid in _PREDATOR_TICKETS:
        criteria.append(AcceptanceCriterion(
            id="AC_SAFE", text="predators are fenced out: the flock survives the foxes prowling "
                               "the pond over 20 ticks", stage=Stage.A,
            check_hint="onepond_predator_safe"))
    if tid in _WATER_TICKETS:
        criteria.append(AcceptanceCriterion(
            id="AC_WATER", text="the flock is watered: every hatchery sits within reach of a well",
            stage=Stage.A, check_hint="onepond_water_access"))
    if tid in _LAUNCH_TICKETS:
        criteria.append(AcceptanceCriterion(
            id="AC3", text="the pond sends geese galactic: at least one goose is launched to "
                            "space within 20 ticks", stage=Stage.A,
            check_hint="onepond_launch_viable"))
    t = Ticket(
        id=tid,
        title=_TITLES[tid],
        kind=TicketKind.SYSTEM,
        acceptance_criteria=criteria,
        references=["game/onepond/iso_camera.json"],
    )
    t.freeze()
    return t


def onepond_tickets() -> list[Ticket]:
    return [_ticket(tid) for tid in
            ("T-POND-01", "T-POND-02", "T-POND-03", "T-POND-04", "T-POND-05", "T-POND-06")]


def onepond_generation_client() -> ScriptedGenerationClient:
    """Icarus stand-in: emit the target One Pond config for the ticket being built."""
    def script(packet) -> dict[str, str]:
        config = POND_CONFIGS.get(packet.ticket.id, POND_CONFIGS["T-POND-01"])
        return {"onepond_config.json": json.dumps(config, indent=2, sort_keys=True)}

    return ScriptedGenerationClient(script, model_id="icarus-onepond-scripted")
