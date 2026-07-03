"""Behaviour lock for the Icarus-built command parser (OP-29)."""

from __future__ import annotations

from game.pond.parse_command import parse_command


def test_verb_and_target_lowercased():
    assert parse_command("Build Bakery") == ("build", "bakery")
    assert parse_command("place well now") == ("place", "well")   # extra words ignored


def test_missing_target_and_blank():
    assert parse_command("quit") == ("quit", "")
    assert parse_command("   ") == ("", "")
