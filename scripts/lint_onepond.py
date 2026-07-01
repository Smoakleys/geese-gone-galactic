"""Dry-run a One Pond config through Stage A — a design/debug lint, no build.

`run_onepond_autopilot.py` builds and accepts tickets; this is the complementary diagnostic:
point it at a hand-authored (or generated) `onepond_config.json` and it runs the *same*
certified Stage-A registry the harness uses, printing each check's PASS/FAIL/SKIP with evidence
and exiting non-zero if the layout wouldn't clear the gate. Nothing is built, committed, or
reviewed — it just tells you why a pond design would (or wouldn't) get through.

Examples:
    python scripts/lint_onepond.py game/onepond/fixtures/economy_solvency/good/onepond_config.json
    python scripts/lint_onepond.py my_pond.json
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.onepond.checks import CONFIG_NAME, build_onepond_registry
from harness.checks.registry import stage_a_passed
from harness.models import Result, Ticket, TicketKind


def lint(config_path: Path) -> int:
    """Run certified Stage A on ``config_path``. Returns 0 if it would pass, else 1."""
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"no such config: {config_path}")
        return 2

    work = Path(tempfile.mkdtemp(prefix="onepond_lint_"))
    try:
        artifact = work / "artifact"
        artifact.mkdir()
        shutil.copyfile(config_path, artifact / CONFIG_NAME)
        registry = build_onepond_registry(work / "lock")
        ticket = Ticket(id="__lint__", title="lint", kind=TicketKind.SYSTEM, acceptance_criteria=[])
        results = registry.run_stage_a(artifact, ticket)

        print(f"lint {config_path}")
        for r in results:
            mark = {Result.PASS: "PASS", Result.FAIL: "FAIL", Result.SKIP: "skip"}[r.result]
            print(f"  [{mark}] {r.check_id:26} {r.evidence}")
        passed = stage_a_passed(results)
        print(f"\nStage A: {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dry-run a One Pond config through Stage A.")
    ap.add_argument("config", help="path to an onepond_config.json to lint")
    args = ap.parse_args(argv)
    return lint(Path(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
