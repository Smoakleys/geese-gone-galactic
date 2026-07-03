"""The local Ollama Stage-B reviewer client fails CLOSED (offline-safe)."""

from __future__ import annotations

from harness.review.model_client import (
    ChatClient,
    CriterionQuestion,
    ModelRequest,
    OllamaChatClient,
)


def _req():
    return ModelRequest(ticket_id="t", criteria_hash="h", system="review",
                        questions=[CriterionQuestion("AC1", "does X"), CriterionQuestion("AC2", "does Y")],
                        artifact_text={"a.py": "print(1)"})


def test_ollama_chat_client_is_a_chat_client():
    assert isinstance(OllamaChatClient(), ChatClient)


def test_ollama_chat_client_fails_closed_on_transport_error():
    # nothing is listening on this port -> the call errors -> every criterion answered FAIL, never PASS
    client = OllamaChatClient(endpoint="http://127.0.0.1:9", timeout=2.0)
    reply = client.complete(_req())
    assert [a.criterion_id for a in reply.answers] == ["AC1", "AC2"]
    assert all(a.passed is False for a in reply.answers)   # a reviewer that can't answer never approves
