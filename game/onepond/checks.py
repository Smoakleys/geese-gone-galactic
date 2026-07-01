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


def build_onepond_registry(lock_dir: Path):
    """A registry with the harness default checks plus the One Pond game checks, certified."""
    from harness.checks.builtin import default_registry

    reg = default_registry(lock_dir)          # non_empty + code + CV checks (already certified)
    reg.register(PlacementValidCheck())
    reg.register(EconomySolvencyCheck())
    reg.certify_all()                          # re-certify the whole set, rewrite the lock
    return reg
