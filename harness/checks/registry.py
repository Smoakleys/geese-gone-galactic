"""Check discovery, certification, and the committed ``registry.lock``.

Certification is the crux of the whole harness. A check does not become active by
existing in the codebase; it becomes active only by *proving itself* against fixtures:

    green on every good fixture  AND  red on every bad fixture  =>  CERTIFIED

Only CERTIFIED checks run in Stage A. A newly written check that is broken (passes a bad
fixture, or fails a good one) stays inert — it can neither wave bad work through nor wedge
the loop by failing good work. This is what turns "we added a check" into "the check
provably catches the defect it targets and doesn't flag good work."

``registry.lock`` records the fixture content-hashes each check certified against, so the
self-mod validator can detect fixture tampering (swapping in a permissive fixture to
launder a check through certification).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from harness.checks.base import Check
from harness.models import CheckResult, Result, Ticket


LOCK_NAME = "registry.lock"


def _dir_hash(path: Path) -> str:
    """Content hash of a fixture directory: stable over file names + bytes."""
    h = hashlib.sha256()
    if not path.exists():
        return "MISSING"
    for f in sorted(path.rglob("*")):
        if f.is_file():
            rel = f.relative_to(path).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(f.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


@dataclass
class CertificationOutcome:
    check_id: str
    certified: bool
    reason: str
    good_hashes: dict[str, str]
    bad_hashes: dict[str, str]


def certify(check: Check) -> CertificationOutcome:
    """Run a check against its declared fixtures. Certified iff green-on-good, red-on-bad."""
    good_hashes: dict[str, str] = {}
    bad_hashes: dict[str, str] = {}

    if not check.good_fixtures or not check.bad_fixtures:
        return CertificationOutcome(
            check.id, False,
            "a check must declare at least one good AND one bad fixture", good_hashes, bad_hashes,
        )

    for fx in check.good_fixtures:
        good_hashes[str(fx)] = _dir_hash(Path(fx))
        res = check.run(Path(fx), _fixture_ticket())
        if res.result != Result.PASS:
            return CertificationOutcome(
                check.id, False,
                f"failed good fixture {fx}: {res.evidence!r}", good_hashes, bad_hashes,
            )

    for fx in check.bad_fixtures:
        bad_hashes[str(fx)] = _dir_hash(Path(fx))
        res = check.run(Path(fx), _fixture_ticket())
        if res.result == Result.PASS:
            return CertificationOutcome(
                check.id, False,
                f"passed bad fixture {fx} (should have failed)", good_hashes, bad_hashes,
            )

    return CertificationOutcome(check.id, True, "green-on-good, red-on-bad", good_hashes, bad_hashes)


def _fixture_ticket() -> Ticket:
    # Certification runs checks in isolation from any real ticket; a minimal stand-in keeps
    # the Check signature uniform. Checks that need ticket data must not be certified against
    # fixtures that depend on it — kept deliberately simple for the walking skeleton.
    from harness.models import TicketKind
    return Ticket(id="__fixture__", title="fixture", kind=TicketKind.MIXED, acceptance_criteria=[])


class Registry:
    """Holds discovered checks and the certified subset. Persists ``registry.lock``."""

    def __init__(self, lock_dir: Path):
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._checks: dict[str, Check] = {}
        self._certified: dict[str, CertificationOutcome] = {}

    @property
    def lock_path(self) -> Path:
        return self.lock_dir / LOCK_NAME

    def register(self, check: Check) -> None:
        if check.id in self._checks:
            raise ValueError(f"duplicate check id {check.id!r}")
        self._checks[check.id] = check

    def certify_all(self) -> list[CertificationOutcome]:
        """Certify every registered check and (re)write the lock file. Returns all outcomes."""
        outcomes = [certify(c) for c in self._checks.values()]
        self._certified = {o.check_id: o for o in outcomes if o.certified}
        self._write_lock()
        return outcomes

    def certified_checks(self) -> list[Check]:
        return [self._checks[cid] for cid in self._certified]

    def is_certified(self, check_id: str) -> bool:
        return check_id in self._certified

    def _write_lock(self) -> None:
        payload = {
            "certified": {
                cid: {"good_hashes": o.good_hashes, "bad_hashes": o.bad_hashes}
                for cid, o in sorted(self._certified.items())
            }
        }
        self.lock_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    # -- Stage A execution -------------------------------------------------------------

    def run_stage_a(self, artifact_dir: Path, ticket: Ticket) -> list[CheckResult]:
        """Run only CERTIFIED checks, cheapest declared first, fail-fast on a blocking FAIL.

        Ordering: registration order is treated as cost order (static → structural →
        dynamic). The first FAIL short-circuits so an expensive screenshot check never runs
        after a cheap lint has already condemned the artifact.
        """
        results: list[CheckResult] = []
        for check in self.certified_checks():
            if not _applies(check, ticket):
                results.append(CheckResult(check.id, Result.SKIP, "not applicable to ticket kind"))
                continue
            res = check.run(Path(artifact_dir), ticket)
            results.append(res)
            if res.result == Result.FAIL:
                break  # fail-fast
        return results


def _applies(check: Check, ticket: Ticket) -> bool:
    if not check.targets:
        return True
    return ticket.kind.value in check.targets or "*" in check.targets


def stage_a_passed(results: Iterable[CheckResult]) -> bool:
    """Stage A passes only if at least one certified check ran and none FAILed."""
    ran = [r for r in results if r.result != Result.SKIP]
    if not ran:
        return False
    return all(r.result == Result.PASS for r in ran)
