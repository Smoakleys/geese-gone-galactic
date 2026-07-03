"""PythonBehaviorCheck: a deterministic exact-output gate for logic tickets."""

from __future__ import annotations

from harness.checks.behavior import PythonBehaviorCheck
from harness.checks.registry import certify
from harness.models import Result, Ticket, TicketKind


def _ticket(behavior=None):
    return Ticket(id="t", title="t", kind=TicketKind.MIXED, acceptance_criteria=[], behavior=behavior or [])


def test_behavior_check_certifies():
    assert certify(PythonBehaviorCheck()).certified


def test_good_fixture_passes_bad_fails():
    c = PythonBehaviorCheck()
    assert c.run(c.good_fixtures[0], _ticket()).result == Result.PASS
    assert c.run(c.bad_fixtures[0], _ticket()).result == Result.FAIL


def test_reads_ticket_behavior(tmp_path):
    (tmp_path / "m.py").write_text("def f(x):\n    return x * 2\n")
    c = PythonBehaviorCheck()
    assert c.run(tmp_path, _ticket([{"module": "m.py", "call": "f(3)", "expect": 6}])).result == Result.PASS
    assert c.run(tmp_path, _ticket([{"module": "m.py", "call": "f(3)", "expect": 7}])).result == Result.FAIL


def test_skips_without_examples(tmp_path):
    (tmp_path / "m.py").write_text("x = 1\n")
    assert PythonBehaviorCheck().run(tmp_path, _ticket()).result == Result.SKIP


def test_fails_closed_on_missing_module_or_crash(tmp_path):
    c = PythonBehaviorCheck()
    assert c.run(tmp_path, _ticket([{"module": "nope.py", "call": "f()", "expect": 1}])).result == Result.FAIL
    (tmp_path / "m.py").write_text("def f():\n    raise ValueError('boom')\n")
    assert c.run(tmp_path, _ticket([{"module": "m.py", "call": "f()", "expect": 1}])).result == Result.FAIL
