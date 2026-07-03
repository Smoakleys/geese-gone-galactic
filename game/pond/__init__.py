"""The real One Pond game logic (Pond era), built by Icarus through the harness — NOT the legacy
game/onepond python toy. Modules here are agent-built and behaviour-locked by tests (see README.md).

Public API — the composed One Pond game core (build → tick → status → outcome, plus the state→scene
bridge). Every function was produced by the agent under the full gate.
"""

from game.pond.bread_tick import tick
from game.pond.granary import production
from game.pond.placement import is_valid
from game.pond.pond_economy import tick_bread
from game.pond.pond_advice import pond_advice
from game.pond.pond_outcome import pond_outcome
from game.pond.pond_scene import build_body
from game.pond.pond_score import pond_score
from game.pond.pond_state import add_building, step
from game.pond.pond_status import pond_status
from game.pond.predator import is_safe
from game.pond.predator_loss import predator_loss
from game.pond.water_access import has_water

__all__ = [
    "tick", "production", "is_valid", "tick_bread", "pond_outcome",
    "build_body", "pond_score", "pond_advice", "add_building", "step",
    "pond_status", "is_safe", "predator_loss", "has_water",
]
