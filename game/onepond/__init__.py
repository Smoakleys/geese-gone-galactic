"""One Pond — the smallest complete slice of Geese Gone Galactic.

A fixed isometric pond with a handful of low-poly buildings, a bread economy that ticks, and
place-a-building + save. This package is the authoritative simulation; it is what the harness
drives tickets against in Phase 4 to prove the whole loop end-to-end.
"""

from game.onepond.world import (
    BUILDING_TYPES,
    Building,
    World,
    build_world,
    simulate_solvency,
)

__all__ = ["BUILDING_TYPES", "Building", "World", "build_world", "simulate_solvency"]
