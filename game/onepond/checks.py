"""One Pond game checks — deterministic Stage-A gates on the game config artifact.

These make "the game actually works" a mechanical gate, not a reviewer's guess. A builder that
ships a `onepond_config.json` describing an impossible layout (overlapping/out-of-bounds
buildings) or a doomed economy (bread goes negative) is rejected before any subjective review.
They implement the harness ``Check`` contract and certify against committed good/bad fixtures,
so they earn their Stage-A slot exactly like the code/CV checks.

The checks import the authoritative ``game.onepond.world`` model — the same simulation the game
runs — so the gate and the game can never disagree about what "solvent" means.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.checks.base import Check, CheckCost
from harness.models import CheckResult, Result, Ticket
from game.onepond.world import PlacementError, build_world, simulate_solvency

_FIXTURES = Path(__file__).parent / "fixtures"
CONFIG_NAME = "onepond_config.json"
SOLVENCY_HORIZON = 20


def _find_config(artifact_dir: Path) -> Path | None:
    direct = artifact_dir / CONFIG_NAME
    if direct.exists():
        return direct
    hits = [f for f in artifact_dir.rglob(CONFIG_NAME) if f.is_file()]
    return hits[0] if hits else None


class PlacementValidCheck(Check):
    """The One Pond config must describe a legal layout (known types, in-bounds, no overlaps)."""

    id = "onepond_placement_valid"
    targets: list[str] = ["*"]
    cost = CheckCost.STRUCTURAL

    def __init__(self) -> None:
        base = _FIXTURES / "placement_valid"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            world = build_world(config)   # raises PlacementError on any illegal building
        except (PlacementError, KeyError, ValueError) as e:
            return CheckResult(self.id, Result.FAIL, f"illegal One Pond layout: {e}",
                               artifacts=[str(cfg_path)])
        return CheckResult(self.id, Result.PASS, f"{len(world.buildings)} building(s) placed legally",
                           metrics={"onepond_buildings": float(len(world.buildings))})


class EconomySolvencyCheck(Check):
    """The One Pond bread economy must stay solvent over the evaluation horizon."""

    id = "onepond_economy_solvent"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC

    def __init__(self) -> None:
        base = _FIXTURES / "economy_solvency"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            report = simulate_solvency(config, horizon=SOLVENCY_HORIZON)
        except (PlacementError, KeyError, ValueError) as e:
            return CheckResult(self.id, Result.FAIL, f"config will not simulate: {e}",
                               artifacts=[str(cfg_path)])
        if report["buildings"] < 1:
            return CheckResult(self.id, Result.FAIL, "empty pond: no buildings")
        if not report["solvent"]:
            return CheckResult(self.id, Result.FAIL,
                               f"insolvent economy: bread hits {report['min_bread']} "
                               f"within {SOLVENCY_HORIZON} ticks (net {report['net_delta']}/tick)")
        return CheckResult(
            self.id, Result.PASS,
            f"solvent over {SOLVENCY_HORIZON} ticks (min bread {report['min_bread']}, "
            f"net {report['net_delta']}/tick, {report['geese']} geese)",
            metrics={"onepond_min_bread": float(report["min_bread"]),
                     "onepond_net_bread_delta": float(report["net_delta"])},
        )


class LaunchViabilityCheck(Check):
    """A launchpad must actually send geese galactic — dead launch infrastructure is a defect.

    A pond can be perfectly legal and perfectly solvent yet ship a launchpad that never launches
    a single goose (no hatchery feeding it, so the flock is always empty). That is a real, silent
    failure mode: the galactic gate exists but nothing reaches space. This check is scoped to
    ponds that *have* a launchpad — for those it makes "the geese reached space" a mechanical
    Stage-A gate and mints ``onepond_launched`` as a ratchet floor, so once a pond launches N
    geese the harness can never accept a regression below N. Ponds with no launchpad (the earlier
    build-up tickets) are out of scope and SKIP.
    """

    id = "onepond_launch_viable"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC

    def __init__(self) -> None:
        base = _FIXTURES / "launch_viable"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            report = simulate_solvency(config, horizon=SOLVENCY_HORIZON)
        except (PlacementError, KeyError, ValueError) as e:
            return CheckResult(self.id, Result.FAIL, f"config will not simulate: {e}",
                               artifacts=[str(cfg_path)])
        if report["launch_capacity"] < 1:
            return CheckResult(self.id, Result.SKIP, "no launchpad in pond; launch not in scope")
        if report["launched"] < 1:
            return CheckResult(self.id, Result.FAIL,
                               f"launchpad present but no geese reached space over "
                               f"{SOLVENCY_HORIZON} ticks (feed it with a hatchery)")
        return CheckResult(
            self.id, Result.PASS,
            f"{report['launched']} geese sent galactic over {SOLVENCY_HORIZON} ticks",
            metrics={"onepond_launched": float(report["launched"])},
        )


class LivelinessCheck(Check):
    """A pond that builds flock infrastructure must actually keep a living flock.

    Harvested from the flywheel: Stage-B reviewers kept rejecting ponds that were legal and
    solvent yet "read as dead" — a granary raising goose *capacity* for a flock that is never
    hatched, so nothing on the pond is ever alive. That is a real, silent failure mode the
    deterministic gates missed (placement is legal, the economy is solvent, and with no
    launchpad the launch check does not apply). This mechanizes the reviewers' subjective
    "lifeless pond" judgement: scoped to ponds that invest in a granary (goose capacity), it
    fails any that hatch zero geese over the horizon, and mints ``onepond_geese_hatched`` as a
    ratchet floor so a pond's living flock can never silently regress to zero. Bare build-up
    ponds with no granary (e.g. the first-bakery ticket) are out of scope and SKIP — a lone
    bakery is legitimately not yet alive.
    """

    id = "onepond_liveliness"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC

    def __init__(self) -> None:
        base = _FIXTURES / "liveliness"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            report = simulate_solvency(config, horizon=SOLVENCY_HORIZON)
        except (PlacementError, KeyError, ValueError) as e:
            return CheckResult(self.id, Result.FAIL, f"config will not simulate: {e}",
                               artifacts=[str(cfg_path)])
        has_granary = any(b.get("type") == "granary" for b in config.get("buildings", []))
        if not has_granary:
            return CheckResult(self.id, Result.SKIP,
                               "no granary: flock-capacity liveliness not in scope")
        hatched = int(report["geese"]) + int(report["launched"])
        if hatched < 1:
            return CheckResult(self.id, Result.FAIL,
                               f"lifeless pond: granary provides goose capacity but no geese are "
                               f"hatched over {SOLVENCY_HORIZON} ticks (add a hatchery)",
                               artifacts=[str(cfg_path)])
        return CheckResult(
            self.id, Result.PASS,
            f"living flock: {hatched} geese hatched over {SOLVENCY_HORIZON} ticks",
            metrics={"onepond_geese_hatched": float(hatched)},
        )


class PredatorSafetyCheck(Check):
    """A pond that lets predators in must fence the flock, or the geese are eaten.

    The predator mechanic gives One Pond a genuine new failure mode: a pond can declare foxes
    prowling it (``"predators": n``) for theme/challenge, but every un-fenced predator eats a
    goose per tick. A builder that adds predators without enough ``fence`` buildings ships a
    pond whose flock is silently culled to nothing — legal, solvent, and (with a launchpad) it
    may even look busy, yet the geese keep dying. This mechanizes that: scoped to ponds that
    both invite predators AND hatch geese, it fails any where no goose survives predation over
    the horizon, and mints ``onepond_geese_protected`` as a ratchet floor so a pond's protected
    flock can never silently regress to zero. Predator-free ponds, or ponds with no hatchery to
    protect, are out of scope and SKIP.
    """

    id = "onepond_predator_safe"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC

    def __init__(self) -> None:
        base = _FIXTURES / "predator_safe"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            report = simulate_solvency(config, horizon=SOLVENCY_HORIZON)
        except (PlacementError, KeyError, ValueError) as e:
            return CheckResult(self.id, Result.FAIL, f"config will not simulate: {e}",
                               artifacts=[str(cfg_path)])
        if int(report["predators"]) < 1:
            return CheckResult(self.id, Result.SKIP, "no predators: safety not in scope")
        has_hatchery = any(b.get("type") == "hatchery" for b in config.get("buildings", []))
        if not has_hatchery:
            return CheckResult(self.id, Result.SKIP, "no hatchery: no flock to protect")
        survivors = int(report["geese"]) + int(report["launched"])
        if survivors < 1:
            return CheckResult(self.id, Result.FAIL,
                               f"predators cull the flock: {report['effective_predators']} un-fenced "
                               f"predator(s) leave no goose alive over {SOLVENCY_HORIZON} ticks "
                               f"(add fences)", artifacts=[str(cfg_path)])
        return CheckResult(
            self.id, Result.PASS,
            f"flock protected: {survivors} geese survived {report['predators']} predator(s) "
            f"over {SOLVENCY_HORIZON} ticks ({report['eaten']} lost)",
            metrics={"onepond_geese_protected": float(survivors)},
        )


class CohesionCheck(Check):
    """Buildings must read as one pond, not clutter scattered across the grid.

    This is the harness's own flywheel output made concrete: Stage-B reviewers kept rejecting
    ponds whose buildings sprawled to opposite corners ("doesn't read as one pond; feels like
    clutter") — a subjective ``cohesion`` defect. Stage C's ``DecisionLogReview`` clustered that
    recurring defect and proposed a check id of ``auto_cohesion_check`` (``auto_`` + the defect
    criterion). This check *is* that proposal realized: its id is exactly what Stage C proposed,
    so a subjective judgement reviewers made by hand is now a mechanical Stage-A gate. It fails
    layouts whose compactness (buildings per bounding-box cell) falls below a floor, and mints
    ``onepond_cohesion`` as a ratchet floor. Ponds with fewer than two buildings SKIP (cohesion
    is undefined for a single building).
    """

    id = "auto_cohesion_check"      # the id Stage C proposed for the recurring 'cohesion' defect
    targets: list[str] = ["*"]
    cost = CheckCost.STRUCTURAL
    MIN_COMPACTNESS = 0.25

    def __init__(self) -> None:
        base = _FIXTURES / "cohesion"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        cfg_path = _find_config(Path(artifact_dir))
        if cfg_path is None:
            return CheckResult(self.id, Result.SKIP, f"no {CONFIG_NAME} in artifact")
        try:
            config = json.loads(cfg_path.read_text())
            coords = [(int(b["x"]), int(b["y"])) for b in config.get("buildings", [])]
        except (KeyError, ValueError, TypeError) as e:
            return CheckResult(self.id, Result.FAIL, f"unreadable layout: {e}",
                               artifacts=[str(cfg_path)])
        if len(coords) < 2:
            return CheckResult(self.id, Result.SKIP, "fewer than two buildings; cohesion undefined")
        xs = [x for x, _ in coords]
        ys = [y for _, y in coords]
        bbox = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
        compactness = len(coords) / bbox
        if compactness < self.MIN_COMPACTNESS:
            return CheckResult(self.id, Result.FAIL,
                               f"scattered layout: {len(coords)} buildings sprawl across a "
                               f"{bbox}-cell area (compactness {compactness:.2f} < "
                               f"{self.MIN_COMPACTNESS}); cluster them into one pond",
                               artifacts=[str(cfg_path)])
        return CheckResult(self.id, Result.PASS,
                           f"cohesive layout: {len(coords)} buildings, compactness {compactness:.2f}",
                           metrics={"onepond_cohesion": float(compactness)})


def build_onepond_registry(lock_dir: Path):
    """A registry with the harness default checks plus the One Pond game checks, certified."""
    from harness.checks.builtin import default_registry

    reg = default_registry(lock_dir)          # non_empty + code + CV checks (already certified)
    reg.register(PlacementValidCheck())
    reg.register(EconomySolvencyCheck())
    reg.register(LaunchViabilityCheck())
    reg.register(LivelinessCheck())
    reg.register(PredatorSafetyCheck())
    reg.register(CohesionCheck())              # harvested from a Stage-C proposal (auto_cohesion_check)
    reg.certify_all()                          # re-certify the whole set, rewrite the lock
    return reg
