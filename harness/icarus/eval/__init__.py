"""Icarus capability evaluation — the honest scorecard.

Procedural task generators (Hermes/Reasoning-Gym lesson: infinite, non-memorizable instances with
deterministic verifiers) + a runner that drives the agent loop and scores UNAIDED pass rate. This is
how we see Icarus's problem-solving actually climb, rather than trusting a fixed, leak-prone set.
"""

from harness.icarus.eval.capability import (
    ScoreReport,
    TaskInstance,
    TaskResult,
    default_generators,
    run_battery,
    sample_battery,
)

__all__ = [
    "ScoreReport",
    "TaskInstance",
    "TaskResult",
    "default_generators",
    "run_battery",
    "sample_battery",
]
