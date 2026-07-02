"""Tests for the email digest notifier (ops/notify.py) — all offline, no real SMTP."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "ops"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import notify


def test_send_email_dry_run_when_unconfigured(capsys, monkeypatch):
    # No config -> harmless console dry-run, returns False, never raises or hits the network.
    monkeypatch.setattr(notify.NotifyConfig, "load", staticmethod(lambda: None))
    assert notify.send_email("subj", "body") is False
    out = capsys.readouterr().out
    assert "dry-run" in out and "subj" in out


def test_send_email_uses_smtp_ssl_when_configured(monkeypatch):
    # With a config on port 465, it logs in and sends via SMTP_SSL — captured, not real.
    cfg = notify.NotifyConfig(smtp_host="smtp.example.com", smtp_port=465,
                              username="u@example.com", app_password="secret",
                              sender="u@example.com", to="owner@example.com")
    sent = {}

    class _FakeSMTP:
        def __init__(self, host, port, context=None):
            sent["host"], sent["port"] = host, port
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, user, pw): sent["login"] = (user, pw)
        def send_message(self, msg):
            sent["to"] = msg["To"]; sent["subject"] = msg["Subject"]

    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", _FakeSMTP)
    assert notify.send_email("hello", "world", cfg) is True
    assert sent["host"] == "smtp.example.com" and sent["port"] == 465
    assert sent["login"] == ("u@example.com", "secret")
    assert sent["to"] == "owner@example.com" and sent["subject"] == "hello"


def test_build_digest_summarizes_recent_changes():
    subject, body, head = build = notify.build_digest()
    assert subject.startswith("GGG harness:")
    assert len(head) >= 7                                   # a real HEAD sha
    assert "Repo:" in body and "HEAD" in body
    # docs/AUTOPILOT.md carries a "→ NNN passed" line, so the test count should surface.
    assert "tests green" in subject or "passing" in body


def test_config_load_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(notify, "CONFIG_PATH", tmp_path / "nope.json")
    assert notify.NotifyConfig.load() is None
