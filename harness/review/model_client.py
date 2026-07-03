"""The model-client seam for Stage-B review.

A reviewer must not care *which* model answers it — a local model, a scripted stub, or a
fresh zero-context Opus session. Everything above this seam speaks in ``ModelRequest`` /
``ModelReply`` and never imports an SDK. That keeps the governance tests fully offline and
deterministic while leaving a real Anthropic client as a drop-in for production.

The reply contract is deliberately narrow: a model returns a per-criterion PASS/FAIL with
evidence, nothing more. It has **no** authority to declare an overall verdict — that is
*derived* (default-FAIL) by ``harness.models.Verdict`` from these per-criterion answers, so a
model that tries to wave the whole packet through cannot: an unaddressed criterion is a FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class CriterionQuestion:
    """One decomposed, independently-answerable question put to the model."""

    id: str
    text: str
    rubric_ref: Optional[str] = None


@dataclass
class ModelRequest:
    """What a reviewer hands the model: the packet, decomposed into per-criterion questions.

    ``image_paths`` carries rendered artifact/reference images for a vision model; text-only
    reviews leave it empty. No decision log, no prior verdicts, no loop memory ever appears
    here — the request is built from the isolated ``ReviewPacket`` only.
    """

    ticket_id: str
    criteria_hash: str
    system: str
    questions: list[CriterionQuestion]
    artifact_text: dict[str, str] = field(default_factory=dict)
    image_paths: list[str] = field(default_factory=list)
    reference_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CriterionAnswer:
    criterion_id: str
    passed: bool
    evidence: str = ""


@dataclass
class ModelReply:
    model_id: str
    answers: list[CriterionAnswer]

    def by_id(self) -> dict[str, CriterionAnswer]:
        return {a.criterion_id: a for a in self.answers}


@runtime_checkable
class ChatClient(Protocol):
    """The one method above-seam code may call. Implementations may hit an API or be scripted."""

    model_id: str

    def complete(self, request: ModelRequest) -> ModelReply: ...


class ScriptedChatClient(ChatClient):
    """Deterministic offline client. ``script(request) -> {criterion_id: (passed, evidence)}``.

    Used everywhere in tests so Stage-B behaviour is reproducible with zero API cost. Any
    criterion the script omits is answered FAIL with empty evidence — silence is not approval,
    mirroring the default-FAIL rule one layer up.
    """

    def __init__(self, script: Callable[[ModelRequest], dict[str, tuple[bool, str]]],
                 model_id: str = "scripted"):
        self._script = script
        self.model_id = model_id

    def complete(self, request: ModelRequest) -> ModelReply:
        table = self._script(request)
        answers = []
        for q in request.questions:
            passed, evidence = table.get(q.id, (False, ""))
            answers.append(CriterionAnswer(q.id, bool(passed), evidence))
        return ModelReply(self.model_id, answers)


def always_pass_client(model_id: str = "scripted-pass") -> ScriptedChatClient:
    return ScriptedChatClient(
        lambda req: {q.id: (True, f"{q.id}: satisfied") for q in req.questions},
        model_id=model_id,
    )


def always_fail_client(model_id: str = "scripted-fail") -> ScriptedChatClient:
    return ScriptedChatClient(lambda req: {}, model_id=model_id)


class AnthropicChatClient(ChatClient):
    """Real Stage-B reviewer backed by a fresh zero-context Claude session.

    Imported lazily and only constructed in production; the governance suite never touches it.
    Uses Opus for adversarial review by default (see docs/EXECUTION_PLAN.md Phase 2). Each
    ``complete`` is a brand-new request with no carried state — the "fresh reviewer per round"
    property is structural, not a prompt instruction.
    """

    def __init__(self, model_id: str = "claude-opus-4-8", api_key: Optional[str] = None,
                 max_tokens: int = 1024):
        import os
        self.model_id = model_id
        self._max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; cannot build a real review client")

    def complete(self, request: ModelRequest) -> ModelReply:
        from anthropic import Anthropic  # lazy; optional dependency

        client = Anthropic(api_key=self._api_key)
        content = _render_prompt(request)
        blocks: list[dict] = [{"type": "text", "text": content}]
        for p in request.image_paths:
            blocks.append(_image_block(p))
        msg = client.messages.create(
            model=self.model_id,
            max_tokens=self._max_tokens,
            system=request.system,
            messages=[{"role": "user", "content": blocks}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return ModelReply(self.model_id, _parse_answers(text, request))


class OllamaChatClient(ChatClient):
    """A LOCAL Stage-B reviewer backed by Ollama — a fresh zero-context review each call, no cloud key.

    Reuses the same prompt/parse helpers as the Anthropic path, so the default-FAIL contract holds: a
    criterion the model does not clearly PASS (with evidence) is a FAIL, and any transport/parse failure
    fails CLOSED (all FAIL) — a reviewer that can't answer never waves work through. Point it at a model
    DIFFERENT from the builder where possible, to keep the critic independent.
    """

    def __init__(self, model_id: str = "qwen3:30b", endpoint: str = "http://localhost:11434",
                 timeout: float = 180.0, num_ctx: int = 8192):
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.num_ctx = num_ctx

    def complete(self, request: ModelRequest) -> ModelReply:
        import json
        import urllib.request

        system = request.system or "You are a strict, adversarial reviewer."
        payload = {
            "model": self.model_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": _render_prompt(request)}],
            "stream": False, "keep_alive": "10m",
            "options": {"temperature": 0.1, "num_ctx": self.num_ctx},
        }
        text = ""
        try:
            req = urllib.request.Request(self.endpoint + "/api/chat",
                                         data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read())
            msg = body.get("message", {})
            text = (msg.get("content") or msg.get("thinking") or "")
        except Exception:
            text = ""  # transport failure -> empty -> _parse_answers returns all FAIL (fail-closed)
        return ModelReply(self.model_id, _parse_answers(text, request))


# -- prompt rendering / parsing (production path; kept tiny + testable) ------------------

# Per-artifact character cap in the review prompt. A TEMPLATED Godot scene is
# camera + helpers (~1.8 KB) + the meaningful build(); the old 2 KB cap cut build() off, so the
# reviewer judged scenes nearly blind. 6 KB shows a full scene / long module while staying well inside
# num_ctx (8192). (Note: for ABSTRACT low-poly scenes even a fully-fed text reviewer is an unreliable
# VISUAL judge -- see memory ggg-abstract-visuals-fail-judges; this only removes the truncation blindfold.)
_ARTIFACT_CHAR_CAP = 6000


def _render_prompt(request: ModelRequest) -> str:
    lines = [
        "You are a strict, adversarial reviewer. For EACH criterion below, answer PASS only if",
        "the artifact clearly satisfies it with concrete evidence; otherwise FAIL. Reply with one",
        "line per criterion in the exact form: `<id>: PASS|FAIL — <evidence>`.",
        "",
        "Artifact files:",
    ]
    for name, body in request.artifact_text.items():
        snippet = body if len(body) < _ARTIFACT_CHAR_CAP else body[:_ARTIFACT_CHAR_CAP] + "…"
        lines.append(f"--- {name} ---\n{snippet}")
    lines.append("\nCriteria:")
    for q in request.questions:
        lines.append(f"- {q.id}: {q.text}")
    return "\n".join(lines)


def _parse_answers(text: str, request: ModelRequest) -> list[CriterionAnswer]:
    """Parse `<id>: PASS|FAIL — evidence` lines. Missing/garbled answers default to FAIL."""
    found: dict[str, CriterionAnswer] = {}
    valid_ids = {q.id for q in request.questions}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        cid, rest = line.split(":", 1)
        cid = cid.strip().lstrip("-* ").strip()
        if cid not in valid_ids:
            continue
        rest = rest.strip()
        verdict_token = rest.split()[0].upper() if rest else ""
        passed = verdict_token.startswith("PASS")
        evidence = rest[len(verdict_token):].lstrip(" —-:").strip()
        found[cid] = CriterionAnswer(cid, passed and bool(evidence), evidence)
    return [found.get(q.id, CriterionAnswer(q.id, False, "")) for q in request.questions]


def _image_block(path: str) -> dict:
    import base64
    import mimetypes

    media_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        data = base64.standard_b64encode(fh.read()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}
