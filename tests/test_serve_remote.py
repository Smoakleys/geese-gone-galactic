"""Tests for the remote-control launcher helpers (ops/serve_remote.py) — no real tunnel/network."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "ops"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import serve_remote


def test_extract_tunnel_url_finds_trycloudflare():
    line = "2026-07-01T22:00:00Z INF |  https://calm-forest-1234.trycloudflare.com  |"
    assert serve_remote.extract_tunnel_url(line) == "https://calm-forest-1234.trycloudflare.com"
    assert serve_remote.extract_tunnel_url("no url on this line") is None


def test_resolve_token_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setattr(serve_remote, "TOKEN_PATH", tmp_path / "tok.local")
    monkeypatch.setenv("GGG_DASHBOARD_TOKEN", "env-token")
    assert serve_remote.resolve_token() == "env-token"


def test_resolve_token_generates_and_persists(monkeypatch, tmp_path):
    monkeypatch.delenv("GGG_DASHBOARD_TOKEN", raising=False)
    tok_path = tmp_path / "tok.local"
    monkeypatch.setattr(serve_remote, "TOKEN_PATH", tok_path)
    first = serve_remote.resolve_token()
    assert first and tok_path.read_text().strip() == first
    assert serve_remote.resolve_token() == first  # stable across calls (read back from file)
