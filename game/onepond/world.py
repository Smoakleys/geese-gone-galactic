"""One Pond world model: buildings, the bread economy tick, placement, and save/load.

Deterministic and stdlib-only. The rules are small on purpose — the point of Phase 4 is to
prove the *harness* can drive real game work to acceptance, so the game must be simple enough
to gate deterministically yet real enough to have genuine failure modes (an insolvent economy,
an illegal placement). Those failure modes are exactly what the Phase-4 game checks catch.

Bread economy: each building applies a fixed ``bread_delta`` per tick; placement costs bread
once. A configuration is *solvent* if bread never goes negative over the evaluation horizon.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# The three One Pond buildings. Fixed low-poly assets in Godot; here, just their economics.
BUILDING_TYPES: dict[str, dict] = {
    "bakery":   {"cost": 0, "bread_delta": 3, "geese_delta": 0},   # the producer
    "hatchery": {"cost": 6, "bread_delta": -2, "geese_delta": 1},  # eats bread, hatches geese
    "granary":  {"cost": 3, "bread_delta": 0, "geese_delta": 0},   # neutral; raises capacity
}
GRANARY_CAPACITY_BONUS = 20
BASE_CAPACITY = 20


class PlacementError(ValueError):
    pass


@dataclass(frozen=True)
class Building:
    type: str
    x: int
    y: int


@dataclass
class World:
    grid_w: int = 8
    grid_h: int = 8
    bread: int = 10
    geese: int = 0
    tick_count: int = 0
    buildings: list[Building] = field(default_factory=list)

    # -- placement ---------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        granaries = sum(1 for b in self.buildings if b.type == "granary")
        return BASE_CAPACITY + granaries * GRANARY_CAPACITY_BONUS

    def _occupied(self) -> set[tuple[int, int]]:
        return {(b.x, b.y) for b in self.buildings}

    def can_place(self, btype: str, x: int, y: int) -> tuple[bool, str]:
        if btype not in BUILDING_TYPES:
            return False, f"unknown building type {btype!r}"
        if not (0 <= x < self.grid_w and 0 <= y < self.grid_h):
            return False, f"({x},{y}) out of {self.grid_w}x{self.grid_h} grid"
        if (x, y) in self._occupied():
            return False, f"({x},{y}) already occupied"
        if self.bread < BUILDING_TYPES[btype]["cost"]:
            return False, f"not enough bread for {btype} (need {BUILDING_TYPES[btype]['cost']})"
        return True, "ok"

    def place(self, btype: str, x: int, y: int) -> Building:
        ok, reason = self.can_place(btype, x, y)
        if not ok:
            raise PlacementError(reason)
        self.bread -= BUILDING_TYPES[btype]["cost"]
        b = Building(btype, x, y)
        self.buildings.append(b)
        return b

    # -- economy -----------------------------------------------------------------------

    def net_bread_delta(self) -> int:
        return sum(BUILDING_TYPES[b.type]["bread_delta"] for b in self.buildings)

    def tick(self, n: int = 1) -> None:
        for _ in range(n):
            self.bread = min(self.capacity, self.bread + self.net_bread_delta())
            self.geese += sum(BUILDING_TYPES[b.type]["geese_delta"] for b in self.buildings)
            self.tick_count += 1

    # -- save / load -------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "grid": [self.grid_w, self.grid_h],
            "bread": self.bread,
            "geese": self.geese,
            "tick_count": self.tick_count,
            "buildings": [{"type": b.type, "x": b.x, "y": b.y} for b in self.buildings],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        gw, gh = data.get("grid", [8, 8])
        w = cls(grid_w=int(gw), grid_h=int(gh), bread=int(data.get("bread", 10)),
                geese=int(data.get("geese", 0)), tick_count=int(data.get("tick_count", 0)))
        w.buildings = [Building(b["type"], int(b["x"]), int(b["y"]))
                       for b in data.get("buildings", [])]
        return w

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> "World":
        return cls.from_dict(json.loads(Path(path).read_text()))


def build_world(config: dict) -> World:
    """Construct a World from a One Pond config, validating every placement.

    ``config`` = ``{"grid":[w,h], "start_bread":int, "buildings":[{type,x,y}, ...]}``.
    Raises ``PlacementError`` on any illegal building (bad type, out of bounds, overlap,
    unaffordable at placement time).
    """
    gw, gh = config.get("grid", [8, 8])
    world = World(grid_w=int(gw), grid_h=int(gh), bread=int(config.get("start_bread", 10)))
    for spec in config.get("buildings", []):
        world.place(spec["type"], int(spec["x"]), int(spec["y"]))
    return world


def simulate_solvency(config: dict, horizon: int = 20) -> dict:
    """Build the world and tick it ``horizon`` times, reporting solvency metrics.

    Returns ``{"solvent": bool, "min_bread": int, "net_delta": int, "geese": int}``. A config
    is solvent if bread never goes negative across the horizon (placement costs are charged up
    front by ``build_world``).
    """
    world = build_world(config)
    min_bread = world.bread
    for _ in range(horizon):
        world.tick(1)
        min_bread = min(min_bread, world.bread)
    return {
        "solvent": min_bread >= 0,
        "min_bread": min_bread,
        "net_delta": world.net_bread_delta(),
        "geese": world.geese,
        "buildings": len(world.buildings),
    }
