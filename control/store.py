"""Durable run state: control mode, heartbeat, per-ticket records, and flywheel metrics.

Everything the control surface shows or mutates lives here, JSON-file backed, so it survives a
restart and can be read by an out-of-process dashboard (or a phone hitting the heartbeat
endpoint) without touching the harness core. The store is the *single* place the human's
Start/Stop/Pause intent and the runner's progress meet: the runner reads ``mode`` and writes
``heartbeat``/records; the dashboard writes ``mode`` and reads everything. No other shared
state, so intervention is a single well-defined lever.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ControlMode(str, Enum):
    RUNNING = "RUNNING"   # process pending tickets
    PAUSED = "PAUSED"     # finish nothing new; resumable
    STOPPED = "STOPPED"   # halt; requires an explicit start to resume


@dataclass
class RunRecord:
    ticket_id: str
    final_state: str
    committed: bool
    rounds: int
    escape_hatch: bool
    reason: str = ""
    ts: float = field(default_factory=time.time)


class RunStore:
    """JSON-backed control + telemetry state. Small, synchronous, and safe to read anytime."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._blank())

    # -- persistence -------------------------------------------------------------------

    def _blank(self) -> dict:
        return {
            "mode": ControlMode.RUNNING.value,
            "heartbeat": 0.0,
            "started_at": time.time(),
            "records": [],
            "metrics": {"accepted": 0, "escape_hatch_builds": 0, "review_rounds": []},
            "blocked": [],
            "stage_c_proposals": [],
        }

    def _read(self) -> dict:
        return json.loads(self.path.read_text())

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        tmp.replace(self.path)  # atomic swap; a reader never sees a half-written file

    # -- control mode ------------------------------------------------------------------

    @property
    def mode(self) -> ControlMode:
        return ControlMode(self._read()["mode"])

    def set_mode(self, mode: ControlMode) -> None:
        data = self._read()
        data["mode"] = ControlMode(mode).value
        self._write(data)

    def start(self) -> None:
        self.set_mode(ControlMode.RUNNING)

    def pause(self) -> None:
        self.set_mode(ControlMode.PAUSED)

    def stop(self) -> None:
        self.set_mode(ControlMode.STOPPED)

    # -- heartbeat ---------------------------------------------------------------------

    def beat(self) -> float:
        data = self._read()
        now = time.time()
        data["heartbeat"] = now
        self._write(data)
        return now

    def heartbeat_age(self, now: Optional[float] = None) -> Optional[float]:
        hb = self._read()["heartbeat"]
        if not hb:
            return None
        return (now if now is not None else time.time()) - hb

    # -- records + metrics -------------------------------------------------------------

    def record(self, rec: RunRecord) -> None:
        data = self._read()
        data["records"].append(asdict(rec))
        m = data["metrics"]
        if rec.committed:
            m["accepted"] += 1
            m["review_rounds"].append(rec.rounds)
            if rec.escape_hatch:
                m["escape_hatch_builds"] += 1
        elif rec.final_state not in (None, ""):
            if rec.ticket_id not in data["blocked"]:
                data["blocked"].append(rec.ticket_id)
        self._write(data)

    def records(self) -> list[RunRecord]:
        return [RunRecord(**r) for r in self._read()["records"]]

    def metrics(self) -> dict:
        return self._read()["metrics"]

    def blocked(self) -> list[str]:
        return list(self._read()["blocked"])

    # -- Stage C flywheel proposals ----------------------------------------------------

    def record_proposals(self, proposals: list[dict]) -> None:
        """Overwrite the current set of Stage-C ``ProposedAdjustment`` dicts.

        Harvesting re-scans every staging tree, so the latest run's proposals are the whole
        truth; we replace rather than append to avoid unbounded, stale accumulation.
        """
        data = self._read()
        data["stage_c_proposals"] = list(proposals)
        self._write(data)

    def proposals(self) -> list[dict]:
        return list(self._read().get("stage_c_proposals", []))

    def autonomy_rate(self) -> float:
        """Share of accepted work built with zero escape-hatch (Claude) help. Target -> 1.0."""
        m = self.metrics()
        if m["accepted"] == 0:
            return 0.0
        return (m["accepted"] - m["escape_hatch_builds"]) / m["accepted"]

    def snapshot(self) -> dict:
        """A read-only view for the dashboard/heartbeat endpoint."""
        data = self._read()
        return {
            "mode": data["mode"],
            "heartbeat": data["heartbeat"],
            "heartbeat_age": self.heartbeat_age(),
            "started_at": data["started_at"],
            "metrics": data["metrics"],
            "autonomy_rate": self.autonomy_rate(),
            "accepted": data["metrics"]["accepted"],
            "blocked": data["blocked"],
            "total_records": len(data["records"]),
            "stage_c_proposals": data.get("stage_c_proposals", []),
        }
