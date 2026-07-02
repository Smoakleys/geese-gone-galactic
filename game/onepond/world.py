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

# The One Pond buildings. Fixed low-poly assets in Godot; here, just their economics.
BUILDING_TYPES: dict[str, dict] = {
    "bakery":    {"cost": 0, "bread_delta": 3, "geese_delta": 0},   # the producer
    "hatchery":  {"cost": 6, "bread_delta": -2, "geese_delta": 1},  # eats bread, hatches geese
    "granary":   {"cost": 3, "bread_delta": 0, "geese_delta": 0},   # neutral; raises capacity
    "launchpad": {"cost": 5, "bread_delta": -1, "geese_delta": 0},  # burns bread as fuel, launches geese
    "fence":     {"cost": 2, "bread_delta": 0, "geese_delta": 0},   # neutralizes one prowling predator
    "well":      {"cost": 2, "bread_delta": 0, "geese_delta": 0},   # waters nearby hatcheries
    "training_grounds": {"cost": 4, "bread_delta": -1, "geese_delta": 0},  # musters geese into soldiers
    "command":   {"cost": 5, "bread_delta": -1, "geese_delta": 0},  # spends soldiers to win campaigns
}
GRANARY_CAPACITY_BONUS = 20
BASE_CAPACITY = 20
LAUNCH_RATE = 1  # geese each launchpad sends galactic per tick, drawn from the on-pond flock
PREDATOR_RATE = 1  # geese each un-fenced predator eats per tick, from the standing flock
TRAIN_RATE = 1  # geese each training grounds musters into soldiers per tick, from the flock
CAMPAIGN_COST = 5  # soldier-geese spent per campaign victory at the command building
MAX_TIER = 6  # buildings upgrade T1..T6 (VISION era ladder lives in the tiers, not the map)


class PlacementError(ValueError):
    pass


@dataclass(frozen=True)
class Building:
    type: str
    x: int
    y: int
    tier: int = 1  # T1..T6; scales this building's output (and its up-front cost) linearly


@dataclass
class World:
    grid_w: int = 8
    grid_h: int = 8
    bread: int = 10
    geese: int = 0
    launched: int = 0  # geese sent galactic — the score that makes it Geese Gone Galactic
    soldiers: int = 0  # standing soldier-geese (mustered, not yet spent on a campaign)
    soldiers_total: int = 0  # cumulative soldiers ever trained (never decremented — army raised)
    victories: int = 0  # campaigns won by spending soldiers at the command building
    predators: int = 0  # foxes prowling the pond; each un-fenced one eats a goose per tick
    eaten: int = 0      # geese lost to predators over the run (a failure signal, not a score)
    tick_count: int = 0
    buildings: list[Building] = field(default_factory=list)

    # -- placement ---------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        granary_tiers = sum(b.tier for b in self.buildings if b.type == "granary")
        return BASE_CAPACITY + granary_tiers * GRANARY_CAPACITY_BONUS

    def _occupied(self) -> set[tuple[int, int]]:
        return {(b.x, b.y) for b in self.buildings}

    def can_place(self, btype: str, x: int, y: int, tier: int = 1) -> tuple[bool, str]:
        if btype not in BUILDING_TYPES:
            return False, f"unknown building type {btype!r}"
        if not (1 <= tier <= MAX_TIER):
            return False, f"tier {tier} out of range 1..{MAX_TIER} for {btype}"
        if not (0 <= x < self.grid_w and 0 <= y < self.grid_h):
            return False, f"({x},{y}) out of {self.grid_w}x{self.grid_h} grid"
        if (x, y) in self._occupied():
            return False, f"({x},{y}) already occupied"
        cost = BUILDING_TYPES[btype]["cost"] * tier
        if self.bread < cost:
            return False, f"not enough bread for {btype} T{tier} (need {cost})"
        return True, "ok"

    def place(self, btype: str, x: int, y: int, tier: int = 1) -> Building:
        ok, reason = self.can_place(btype, x, y, tier)
        if not ok:
            raise PlacementError(reason)
        self.bread -= BUILDING_TYPES[btype]["cost"] * tier
        b = Building(btype, x, y, tier)
        self.buildings.append(b)
        return b

    # -- economy -----------------------------------------------------------------------

    def net_bread_delta(self) -> int:
        return sum(BUILDING_TYPES[b.type]["bread_delta"] * b.tier for b in self.buildings)

    @property
    def launch_capacity(self) -> int:
        """Geese sent galactic per tick — each launchpad's throughput scales with its tier."""
        return sum(b.tier for b in self.buildings if b.type == "launchpad") * LAUNCH_RATE

    @property
    def fences(self) -> int:
        """Predator-blocking strength: each fence neutralizes ``tier`` predators."""
        return sum(b.tier for b in self.buildings if b.type == "fence")

    @property
    def train_capacity(self) -> int:
        """Geese mustered into soldiers per tick — each training grounds' throughput scales w/ tier."""
        return sum(b.tier for b in self.buildings if b.type == "training_grounds") * TRAIN_RATE

    @property
    def command_capacity(self) -> int:
        """Campaigns a pond can win per tick — each command building's throughput scales w/ tier."""
        return sum(b.tier for b in self.buildings if b.type == "command")

    @property
    def effective_predators(self) -> int:
        """Predators left prowling after fences neutralize them one-for-one (never negative)."""
        return max(0, self.predators - self.fences) * PREDATOR_RATE

    def tick(self, n: int = 1) -> None:
        for _ in range(n):
            self.bread = min(self.capacity, self.bread + self.net_bread_delta())
            self.geese += sum(BUILDING_TYPES[b.type]["geese_delta"] * b.tier for b in self.buildings)
            # Predators strike after hatching, before launch: an un-fenced pond loses geese from
            # its standing flock. A fully-fenced pond (fences >= predators) loses none.
            eaten = min(self.effective_predators, self.geese)
            self.geese -= eaten
            self.eaten += eaten
            # Muster survivors into soldiers at the training grounds, then launch what's left.
            trained = min(self.train_capacity, self.geese)
            self.geese -= trained
            self.soldiers += trained
            self.soldiers_total += trained
            # Campaigns: each command building spends CAMPAIGN_COST soldiers to win a campaign.
            campaigns = min(self.command_capacity, self.soldiers // CAMPAIGN_COST)
            self.soldiers -= campaigns * CAMPAIGN_COST
            self.victories += campaigns
            # Launch after predation + training: each launchpad sends remaining geese galactic.
            launched = min(self.launch_capacity, self.geese)
            self.geese -= launched
            self.launched += launched
            self.tick_count += 1

    # -- save / load -------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "grid": [self.grid_w, self.grid_h],
            "bread": self.bread,
            "geese": self.geese,
            "launched": self.launched,
            "soldiers": self.soldiers,
            "soldiers_total": self.soldiers_total,
            "victories": self.victories,
            "predators": self.predators,
            "eaten": self.eaten,
            "tick_count": self.tick_count,
            "buildings": [{"type": b.type, "x": b.x, "y": b.y, "tier": b.tier}
                          for b in self.buildings],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        gw, gh = data.get("grid", [8, 8])
        w = cls(grid_w=int(gw), grid_h=int(gh), bread=int(data.get("bread", 10)),
                geese=int(data.get("geese", 0)), launched=int(data.get("launched", 0)),
                soldiers=int(data.get("soldiers", 0)),
                soldiers_total=int(data.get("soldiers_total", 0)),
                victories=int(data.get("victories", 0)),
                predators=int(data.get("predators", 0)), eaten=int(data.get("eaten", 0)),
                tick_count=int(data.get("tick_count", 0)))
        w.buildings = [Building(b["type"], int(b["x"]), int(b["y"]), int(b.get("tier", 1)))
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
    world = World(grid_w=int(gw), grid_h=int(gh), bread=int(config.get("start_bread", 10)),
                  predators=int(config.get("predators", 0)))
    for spec in config.get("buildings", []):
        world.place(spec["type"], int(spec["x"]), int(spec["y"]), int(spec.get("tier", 1)))
    return world


def simulate_solvency(config: dict, horizon: int = 20) -> dict:
    """Build the world and tick it ``horizon`` times, reporting solvency metrics.

    Returns ``{"solvent", "min_bread", "net_delta", "geese", "launched", "buildings"}``. A config
    is solvent if bread never goes negative across the horizon (placement costs are charged up
    front by ``build_world``); ``launched`` is how many geese were sent galactic over the run.
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
        "launched": world.launched,
        "soldiers": world.soldiers,
        "soldiers_total": world.soldiers_total,
        "victories": world.victories,
        "train_capacity": world.train_capacity,
        "command_capacity": world.command_capacity,
        "launch_capacity": world.launch_capacity,
        "predators": world.predators,
        "effective_predators": world.effective_predators,
        "eaten": world.eaten,
        "buildings": len(world.buildings),
        "total_tier": sum(b.tier for b in world.buildings),
    }
