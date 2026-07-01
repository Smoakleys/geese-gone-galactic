"""The Builder seam. The loop talks only to ``Builder.build`` and never learns whether the
builder is a local model, an ensemble, or (in the walking skeleton) a scripted stub.

Design invariant: a builder writes **only** inside ``packet.writable_root`` (the gitignored
staging dir). It has no commit function and no handle to the protected tree. Self-approval
is impossible because there is no approval API to call — the returned ``status`` is a claim
the gate is free to ignore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from harness.models import BuildPacket, BuildResult, BuildStatus


@runtime_checkable
class Builder(Protocol):
    id: str

    def build(self, packet: BuildPacket) -> BuildResult: ...


class StubBuilder(Builder):
    """A scripted builder for the walking skeleton.

    Given a ``script`` mapping round-index -> file contents, it writes ``artifact.txt`` into
    staging on each call. This lets tests drive FAIL-then-PASS sequences deterministically
    with zero LLM cost while exercising the real staging/gate path. A ``None`` payload
    simulates a builder that produced nothing (Stage A should catch it).
    """

    id = "stub"

    def __init__(self, script: Callable[[int], str | None]):
        self._script = script
        self._round = 0

    def build(self, packet: BuildPacket) -> BuildResult:
        root = Path(packet.writable_root)
        root.mkdir(parents=True, exist_ok=True)
        payload = self._script(self._round)
        self._round += 1

        # Always write a decision log — it must reach Stage C but never Stage B (isolation).
        log = root / "decision_log.jsonl"
        with log.open("w") as fh:
            fh.write(json.dumps({
                "step": "compose",
                "choice": "wrote artifact.txt",
                "rationale": "stub builder; payload from test script",
                "alternatives_considered": [],
            }) + "\n")

        if payload is None:
            # Produced nothing usable — Stage A's non_empty_artifact check should FAIL this.
            return BuildResult(BuildStatus.COMPLETED, str(root), str(log), notes="stub produced nothing")

        (root / "artifact.txt").write_text(payload)
        return BuildResult(BuildStatus.COMPLETED, str(root), str(log), notes="stub build")
