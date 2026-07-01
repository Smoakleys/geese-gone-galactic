"""Shared fixtures for the governance test suite.

Each test gets a throwaway git repo so the Gatekeeper's *real* ``git commit`` is exercised
without touching the project repo. The registry uses the harness's bundled fixtures, so
certification runs offline.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Make the repo importable regardless of where pytest is invoked from.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.checks.builtin import default_registry  # noqa: E402
from harness.gatekeeper import Gatekeeper  # noqa: E402
from harness.models import (  # noqa: E402
    AcceptanceCriterion,
    Stage,
    Ticket,
    TicketKind,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@ggg.local")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("temp\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


@pytest.fixture
def registry(tmp_path: Path):
    return default_registry(tmp_path / "lock")


@pytest.fixture
def gatekeeper(git_repo: Path, tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(git_repo, ratchet_dir=tmp_path / "ratchet")


def make_ticket(tid: str = "T-0001", freeze: bool = True) -> Ticket:
    t = Ticket(
        id=tid,
        title="place a bakery",
        kind=TicketKind.MIXED,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC1", text="artifact imports", stage=Stage.A,
                                check_hint="non_empty_artifact"),
            AcceptanceCriterion(id="AC2", text="reads as a bakery vs refs", stage=Stage.B,
                                rubric_ref="visual/rubric/building.md"),
        ],
        references=["refs/bakery_concept.png"],
    )
    if freeze:
        t.freeze()
    return t
