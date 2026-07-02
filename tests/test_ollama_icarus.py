"""Tests for the real (local Ollama) Icarus builder client — all offline (transport mocked)."""

from __future__ import annotations

from harness.icarus.llm_builder import GenerationClient, LLMBuilder
from harness.icarus.ollama_client import OllamaGenerationClient, parse_files
from harness.models import BuildPacket, BuildStatus

from conftest import make_ticket


def test_parse_files_extracts_blocks():
    reply = (
        "junk before\n"
        "===FILE: scenes/pond.tscn===\n[gd_scene]\nline2\n===END===\n"
        "===FILE: scripts/pond.gd===\nextends Node\n===END===\n"
    )
    files = parse_files(reply)
    assert files["scenes/pond.tscn"] == "[gd_scene]\nline2"
    assert files["scripts/pond.gd"] == "extends Node"
    assert parse_files("no files here") == {}          # honest empty -> GAVE_UP upstream


def test_ollama_client_conforms_to_seam_and_builds(tmp_path):
    client = OllamaGenerationClient(model_id="qwen3-coder:30b")
    assert isinstance(client, GenerationClient)         # satisfies the builder seam
    # Mock the HTTP round-trip so no network/model is needed.
    client._chat = lambda system, user: "===FILE: hello.gd===\nextends Node\n===END==="
    packet = BuildPacket(ticket=make_ticket(), writable_root=str(tmp_path / "s"))
    result = LLMBuilder(client).build(packet)
    assert result.status == BuildStatus.COMPLETED
    assert (tmp_path / "s" / "hello.gd").read_text() == "extends Node"


def test_ollama_client_empty_reply_is_honest_giveup(tmp_path):
    client = OllamaGenerationClient()
    client._chat = lambda system, user: "sorry, I can't"   # no ===FILE=== blocks
    packet = BuildPacket(ticket=make_ticket(), writable_root=str(tmp_path / "s"))
    assert LLMBuilder(client).build(packet).status == BuildStatus.GAVE_UP


def test_prompt_includes_criteria_and_defects(tmp_path):
    from harness.models import Defect
    client = OllamaGenerationClient()
    packet = BuildPacket(ticket=make_ticket(), writable_root=str(tmp_path),
                         defects=[Defect(criterion="AC2", severity="blocking", detail="reads as a box")])
    p = client._prompt(packet)
    assert "AC1" in p and "AC2" in p and "reads as a box" in p
