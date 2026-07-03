"""The real One Pond game logic (Pond era), built by Icarus through the harness — NOT the legacy
game/onepond python toy. Modules here are agent-built and behaviour-locked by tests (see README.md).

Public API — the composed One Pond game core (build → tick → status → outcome, plus the state→scene
bridge). Every function was produced by the agent under the full gate.
"""

from game.pond.affordable_buildings import affordable_buildings
from game.pond.bread_tick import tick
from game.pond.build_cost import total_cost
from game.pond.count_by_kind import count_by_kind
from game.pond.goose_count import goose_count
from game.pond.granary import production
from game.pond.nearest_fence import nearest_fence
from game.pond.placement import is_valid
from game.pond.parse_command import parse_command
from game.pond.pond_event import apply_event
from game.pond.pond_economy import tick_bread
from game.pond.pond_advice import pond_advice
from game.pond.pond_outcome import pond_outcome
from game.pond.pond_rank import pond_rank
from game.pond.pond_report import report
from game.pond.pond_scene import build_body
from game.pond.pond_score import pond_score
from game.pond.pond_state import add_building, step
from game.pond.pond_status import pond_status
from game.pond.predator import is_safe
from game.pond.simulate_bread import simulate_bread
from game.pond.sorted_by_distance import sorted_by_distance
from game.pond.predator_loss import predator_loss
from game.pond.unique_kinds import unique_kinds
from game.pond.water_access import has_water

__all__ = [
    "tick", "production", "is_valid", "tick_bread", "pond_outcome",
    "build_body", "pond_score", "pond_advice", "add_building", "step",
    "pond_status", "is_safe", "predator_loss", "has_water", "total_cost", "pond_rank", "goose_count",
    "report", "nearest_fence", "count_by_kind", "sorted_by_distance", "simulate_bread", "unique_kinds",
    "affordable_buildings", "apply_event", "parse_command",
]
