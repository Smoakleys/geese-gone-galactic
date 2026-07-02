"""Deterministic Godot Stage-A checks — the first entries in the engine verifier library.

``godot_parse`` makes "the GDScript actually compiles" a mechanical gate: every ``.gd`` in the
artifact must pass ``godot --headless --check-only``. A broken script is rejected before any
subjective review, and the exact parser error becomes the feedback Icarus's self-repair loop reads.
Fail-closed: if the engine is missing or a script times out, the artifact does NOT pass — an
unverifiable artifact is never a PASS.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from harness.checks.base import Check, CheckCost
from harness.models import CheckResult, Result, Ticket
from game.godot.binary import godot_path

_FIXTURES = Path(__file__).parent / "fixtures"
_TIMEOUT_S = 90.0


class GodotParseCheck(Check):
    """Every ``.gd`` script in the artifact must parse under ``godot --check-only``."""

    id = "godot_parse"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC  # spawns the engine; runs late in Stage A

    def __init__(self) -> None:
        base = _FIXTURES / "godot_parse"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        scripts = sorted(p for p in Path(artifact_dir).rglob("*.gd") if p.is_file())
        if not scripts:
            return CheckResult(self.id, Result.SKIP, "no .gd scripts in artifact")

        godot = godot_path()
        if godot is None:
            return CheckResult(self.id, Result.FAIL, "godot binary not found (ops/bin or PATH)")

        for gd in scripts:
            try:
                # cwd=script dir + relative name mirrors Godot's res:// mapping when there is no
                # project.godot, so a loose generated script parses the same as one in a project.
                proc = subprocess.run(
                    [godot, "--headless", "--check-only", "--script", gd.name],
                    cwd=str(gd.parent), capture_output=True, text=True, timeout=_TIMEOUT_S,
                )
            except subprocess.TimeoutExpired:
                return CheckResult(self.id, Result.FAIL,
                                   f"godot --check-only timed out on {gd.name}", artifacts=[str(gd)])
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                return CheckResult(self.id, Result.FAIL,
                                   f"parse error in {gd.name}: {detail[-600:]}", artifacts=[str(gd)])

        return CheckResult(self.id, Result.PASS,
                           f"{len(scripts)} GDScript file(s) parsed clean",
                           metrics={"godot_scripts_parsed": float(len(scripts))})
