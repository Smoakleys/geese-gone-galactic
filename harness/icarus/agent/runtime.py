"""Icarus' agent runtime: a lean **plan -> act -> reflect** loop.

The model never writes final files directly. Each turn it emits EXACTLY ONE tool call in a
forgiving text protocol (local models are weak at strict JSON function-calling); the runtime
executes it in a sandboxed workspace and feeds the observation back, so the model can *see* what
happened and adapt. The loop is the thing I improve every cycle to raise Icarus's unaided
problem-solving — better tools, better protocol, better memory. The gate (checkers + fresh
critic + scorecard) is a SEPARATE, independent module; this file only *builds*.

Tool protocol (one call per turn), a fenced block:

    ```tool
    name: write_file
    path: hello.py
    body:
    print("HELLO")
    ```

Tools: write_file(path, body) · read_file(path) · run(cmd) · finish(summary).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

_MAX_OUTPUT = 2000  # cap tool output fed back into the (small) context window


# ---------------------------------------------------------------- tool protocol

@dataclass
class ToolCall:
    name: str
    args: dict[str, str]
    body: Optional[str] = None


_TOOL_BLOCK = re.compile(r"```tool[ \t]*\r?\n(.*?)```", re.DOTALL)


def parse_tool_call(text: str) -> Optional[ToolCall]:
    """Parse the LAST ```tool ...``` block. Forgiving ``key: value`` header lines; an optional
    multi-line body starts after a lone ``body:`` line and runs to the end of the block. Returns
    None when no block is present (the loop treats that as 'reflect and try again')."""
    blocks = _TOOL_BLOCK.findall(text)
    if not blocks:
        # Forgiving fallback: an UNCLOSED ```tool block — the model forgot the closing fence or its
        # output was truncated at the context limit. Parse from the opening fence to the end rather
        # than wasting the turn. A properly closed block always wins (handled above).
        m = re.search(r"```tool[ \t]*\r?\n(.*)", text, re.DOTALL)
        if not m:
            return None
        blocks = [m.group(1)]
    lines = blocks[-1].splitlines()
    name = ""
    args: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False
    for line in lines:
        if in_body:
            body_lines.append(line)
            continue
        stripped = line.strip()
        if stripped in ("body:", "body: |", "body:|"):
            in_body = True
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "name":
                name = val
            else:
                args[key] = val
    if not name:
        return None
    body: Optional[str] = "\n".join(body_lines) if body_lines else args.pop("body", None)
    return ToolCall(name=name, args=args, body=body)


# ---------------------------------------------------------------- tool execution

@dataclass
class ToolResult:
    ok: bool
    output: str


def _safe_path(workspace: Path, rel: str) -> Optional[Path]:
    """Resolve ``rel`` inside ``workspace``; None if it escapes (no writing outside the sandbox)."""
    root = workspace.resolve()
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p


_PLACEHOLDER_BODY = re.compile(r"^\s*<[^\n>]{0,60}>\s*$")


def _is_placeholder_body(body: str) -> bool:
    """True if a write_file body is just a `<...>` placeholder token (e.g. `<code>`, `<file contents>`,
    `<your code here>`) -- a common gpt-oss confusion with the protocol's `body:` example that produces a
    file which does nothing. Real one-line code (`print(1)`) is not matched."""
    return bool(_PLACEHOLDER_BODY.match(body))


def exec_tool(call: ToolCall, workspace: Path, *, run_timeout: float = 60.0,
              vision: "Optional[VisionModel]" = None,
              notebook: "Optional[Notebook]" = None,
              render_fn: "Optional[Callable[[Path, Path], tuple[bool, str]]]" = None) -> ToolResult:
    """Execute one tool call in the sandboxed workspace. Never raises — a tool failure is an
    observation the agent reflects on, not a crash. ``vision`` enables ``see``; ``notebook`` ``note``;
    ``render_fn`` enables ``render`` (turn a scene file into a PNG the agent can then ``see``)."""
    workspace = Path(workspace)
    name = call.name

    if name == "write_file":
        rel = call.args.get("path", "").strip()
        if not rel:
            return ToolResult(False, "write_file needs a 'path'")
        p = _safe_path(workspace, rel)
        if p is None:
            return ToolResult(False, f"path escapes the workspace: {rel!r}")
        content = call.body or ""
        if _is_placeholder_body(content):
            # gpt-oss sometimes copies the protocol's `body:` PLACEHOLDER (`<code>`, `<file contents>`)
            # literally instead of writing real content -> the file "runs" but prints nothing (a whole class
            # of empty-output failures in the battery). Reject it so it must write the ACTUAL code.
            return ToolResult(False, "that body is a PLACEHOLDER, not real content. Write the ACTUAL file "
                              "contents after `body:` (real code, e.g. `print(...)`), NOT a `<...>` token.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(True, f"wrote {rel} ({len(content)} bytes)")

    if name == "read_file":
        rel = call.args.get("path", "").strip()
        p = _safe_path(workspace, rel)
        if p is None or not p.is_file():
            return ToolResult(False, f"no such file in workspace: {rel!r}")
        return ToolResult(True, p.read_text(encoding="utf-8", errors="replace")[:_MAX_OUTPUT])

    if name == "run":
        cmd = (call.args.get("cmd", "") or (call.body or "")).strip()
        if not cmd:
            return ToolResult(False, "run needs a 'cmd'")
        try:
            proc = subprocess.run(cmd, shell=True, cwd=str(workspace),
                                  capture_output=True, text=True, timeout=run_timeout)
        except subprocess.TimeoutExpired:
            return ToolResult(False, f"command timed out after {run_timeout:.0f}s: {cmd}")
        combined = (proc.stdout or "")
        if proc.stderr:
            combined += "\n[stderr]\n" + proc.stderr
        # Keep the END, not the start: a Python traceback's `SomeError: message` and a Godot error are the
        # LAST lines, and stderr is appended after stdout — so `[:cap]` on long output cut the actual error
        # off entirely and Icarus couldn't fix what it never saw. Tail-truncate so the error always shows.
        out = combined.strip()
        if len(out) > _MAX_OUTPUT:
            out = "...(head truncated; showing the end where errors/results appear)...\n" + out[-_MAX_OUTPUT:]
        return ToolResult(proc.returncode == 0, f"exit={proc.returncode}\n{out}")

    if name == "list_files":
        rel = (call.args.get("path", ".") or ".").strip()
        base = _safe_path(workspace, rel)
        if base is None or not base.exists():
            return ToolResult(False, f"no such path: {rel!r}")
        root = workspace.resolve()
        files: list[str] = []
        for p in sorted(base.rglob("*")):
            if p.is_file():
                files.append(str(p.relative_to(root)).replace("\\", "/"))
                if len(files) >= 200:
                    files.append("... (truncated)")
                    break
        return ToolResult(True, ("\n".join(files) if files else "(no files)")[:_MAX_OUTPUT])

    if name == "search":
        query = (call.args.get("query", "") or call.args.get("q", "")).strip()
        if not query:
            return ToolResult(False, "search needs a 'query'")
        rel = (call.args.get("path", ".") or ".").strip()
        base = _safe_path(workspace, rel)
        if base is None or not base.exists():
            return ToolResult(False, f"no such path: {rel!r}")
        try:
            pat = re.compile(query)
        except re.error:
            pat = re.compile(re.escape(query))
        root = workspace.resolve()
        hits: list[str] = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pat.search(line):
                    relp = str(p.relative_to(root)).replace("\\", "/")
                    hits.append(f"{relp}:{i}: {line.strip()[:160]}")
                    if len(hits) >= 50:
                        break
            if len(hits) >= 50:
                hits.append("... (truncated)")
                break
        return ToolResult(True, ("\n".join(hits) if hits else f"no matches for {query!r}")[:_MAX_OUTPUT])

    if name == "see":
        rel = (call.args.get("path", "") or "").strip()
        p = _safe_path(workspace, rel)
        if p is None or not p.is_file():
            return ToolResult(False, f"no such image in workspace: {rel!r}")
        if vision is None:
            return ToolResult(False, "no vision model available (the 'see' tool is disabled)")
        question = (call.args.get("question") or call.body
                    or "Describe this image in detail. What objects and layout do you see?")
        try:
            desc = vision.describe(str(p), question)
        except Exception as e:  # a vision failure is an observation, not a crash
            return ToolResult(False, f"vision error: {type(e).__name__}: {e}")
        return ToolResult(True, (desc or "(vision returned nothing)")[:_MAX_OUTPUT])

    if name == "render":
        rel = (call.args.get("path", "scene.gd") or "scene.gd").strip()
        out_rel = (call.args.get("out", "_render.png") or "_render.png").strip()
        src = _safe_path(workspace, rel)
        out = _safe_path(workspace, out_rel)
        if src is None or not src.is_file():
            return ToolResult(False, f"no such file to render: {rel!r}")
        if out is None:
            return ToolResult(False, f"bad output path: {out_rel!r}")
        if render_fn is None:
            return ToolResult(False, "no renderer available (the 'render' tool is disabled)")
        try:
            ok, detail = render_fn(src, out)
        except Exception as e:  # a render failure is an observation, not a crash
            return ToolResult(False, f"render error: {type(e).__name__}: {e}")
        return ToolResult(ok, (f"{detail}; saved to {out_rel} - use 'see' to inspect it"
                               if ok else detail))

    if name == "note":
        text = (call.args.get("text") or call.body or "").strip()
        if not text:
            return ToolResult(False, "note needs 'text' (a lesson/strategy to remember)")
        if notebook is None:
            return ToolResult(True, "noted (ephemeral - no persistent notebook this run)")
        saved = notebook.append(text)
        return ToolResult(True, f"saved to notebook: {text[:80]}" if saved
                          else "already in notebook (skipped duplicate)")

    return ToolResult(False, f"unknown tool: {name!r} "
                      "(use write_file|read_file|list_files|search|run|see|render|note|finish)")


# ---------------------------------------------------------------- model seam

@runtime_checkable
class AgentModel(Protocol):
    """Chat seam: given the running message list, return the model's next reply."""
    def complete(self, messages: list[dict[str, str]]) -> str: ...


@runtime_checkable
class VisionModel(Protocol):
    """Vision seam (Icarus's eyes): describe an image, optionally answering a question about it."""
    def describe(self, image_path: str, question: str) -> str: ...


class ScriptedAgentModel:
    """Deterministic stand-in for tests: returns canned replies in order (then keeps finishing)."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self._i = 0

    def complete(self, messages: list[dict[str, str]]) -> str:  # noqa: D401
        if self._i >= len(self._replies):
            return "```tool\nname: finish\nsummary: out of scripted replies\n```"
        reply = self._replies[self._i]
        self._i += 1
        return reply


# ---------------------------------------------------------------- the loop

class State(str, Enum):
    DONE = "DONE"            # the agent called finish
    MAX_STEPS = "MAX_STEPS"  # ran out of steps
    STUCK = "STUCK"          # repeatedly failed to emit a valid tool call


@dataclass
class AgentResult:
    state: State
    steps: int
    plan: str                       # the approach it stated first (the artifact the critic grades)
    transcript: list[dict[str, str]]
    workspace: str
    finished: bool


_SYSTEM = """You are Icarus, a tool-driving coding agent. You act by emitting tool calls, one per turn.

Be STUBBORN and RESOURCEFUL. When something fails, do NOT give up and do NOT repeat the same call: read the
error, say in one line WHY it failed, then try a DIFFERENT approach (another method, tool, or angle) until
it works. Verify your work (run it / render + see it) BEFORE you finish. Figuring a way around obstacles is
the whole job.

Respond with EXACTLY ONE fenced tool block and NOTHING ELSE (no prose outside the block):
```tool
name: <write_file|read_file|list_files|search|run|see|render|note|finish>
path: <relative path>      # write_file / read_file / list_files / search (dir) / see (image) / render (scene)
out: <output png path>     # render (renders a scene file to a PNG you can then 'see')
query: <text or regex>     # search
question: <what to look for>  # see (describe/inspect an image)
text: <lesson to remember>   # note (save a durable lesson for future tasks)
cmd: <shell command>       # run
summary: <what you did>    # finish
body:
<file contents>            # write_file only; everything after 'body:' is the file
```

Example:
```tool
name: write_file
path: greet.py
body:
print("HELLO GEESE")
```"""


def _extract_plan(reply: str) -> str:
    before = reply.split("```tool", 1)[0].strip()
    return before[:400] if before else "(no plan stated)"


_CONTEXT_KEEP_RECENT = 8  # most-recent conversation messages kept verbatim when trimming
# The CURATED notebook is injected whole; 2000 chars silently cut off the LATER lessons (e.g. the Godot-4
# `.position` not `.translation` rule at char ~2586) so Icarus never saw them — it then made exactly that
# mistake in OP-35. The seed is bounded + high-signal, so inject it in full within num_ctx (8192).
_NOTEBOOK_CHAR_CAP = 8000


def _trim_context(messages: "list[dict[str, str]]", plan: str) -> "list[dict[str, str]]":
    """Bound the context SENT to the model so a long run stays fast (the plan's 'trim raw tool output
    after use'). Keeps the setup (system + task, and the notebook if present) and the most-recent
    exchanges; older middle turns collapse to a one-line marker carrying the plan. The full transcript
    is untouched — only the model's input shrinks, so per-turn prompt cost stops growing with steps."""
    first_assistant = next((i for i, m in enumerate(messages) if m["role"] == "assistant"), len(messages))
    head, convo = messages[:first_assistant], messages[first_assistant:]
    if len(convo) <= _CONTEXT_KEEP_RECENT:
        return messages
    marker = {"role": "user", "content":
              f"[{len(convo) - _CONTEXT_KEEP_RECENT} earlier steps trimmed to save context. "
              f"Your plan: {plan[:200]}]"}
    return head + [marker] + convo[-_CONTEXT_KEEP_RECENT:]


def run_agent(model: AgentModel, task: str, workspace: Path, *,
              max_steps: int = 12, run_timeout: float = 60.0,
              vision: "Optional[VisionModel]" = None,
              notebook: "Optional[Notebook]" = None, use_notebook: bool = True,
              render_fn: "Optional[Callable[[Path, Path], tuple[bool, str]]]" = None) -> AgentResult:
    """Drive the plan->act->reflect loop until the agent finishes, gets stuck, or runs out of steps.

    Returns an :class:`AgentResult` including the stated plan (the approach artifact) and the full
    transcript (the trajectory the fresh critic and the scorecard can inspect). ``use_notebook=False``
    strips cross-task memory to measure unaided capability (the dependence-gap discipline)."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM}]
    if notebook is not None and use_notebook:
        nb = notebook.read().strip()
        if nb:
            messages.append({"role": "user", "content":
                             "NOTEBOOK - lessons you saved from past tasks; use them:\n"
                             + nb[:_NOTEBOOK_CHAR_CAP]})
    messages.append({"role": "user", "content": f"TASK:\n{task}\n\nEmit your first tool call now."})
    plan = ""
    consecutive_bad = 0
    consecutive_errors = 0
    wrote_files = False          # did it produce an artifact...
    verified = False             # ...and actually run/render/see it before finishing?
    nudged_verify = False        # the verify reminder fires at most once (never blocks finishing outright)
    hinted_finish = False        # the "you've verified -> finish if satisfied" cue fires at most once
    steps = 0
    for steps in range(1, max_steps + 1):
        try:
            reply = model.complete(_trim_context(messages, plan))
        except Exception as e:  # model/network failure must not crash the loop — degrade to STUCK
            consecutive_bad += 1
            if consecutive_bad >= 3:
                return AgentResult(State.STUCK, steps, plan, messages, str(workspace), False)
            messages.append({"role": "user",
                             "content": f"(model call failed: {type(e).__name__}: {e}; try again)"})
            continue
        messages.append({"role": "assistant", "content": reply})
        if not plan:
            plan = _extract_plan(reply)

        call = parse_tool_call(reply)
        if call is None:
            consecutive_bad += 1
            if consecutive_bad >= 3:
                # Observed with gpt-oss: after building + rendering a good scene it emits a prose summary
                # instead of a `finish` tool call. If it already VERIFIED its work (ran/rendered), treat that
                # as an implicit finish -> DONE, not STUCK -- the artifact is produced + verified, and the
                # gate still decides quality regardless of this state. Only STUCK if it never got anywhere.
                if verified:
                    return AgentResult(State.DONE, steps, plan, messages, str(workspace), True)
                return AgentResult(State.STUCK, steps, plan, messages, str(workspace), False)
            messages.append({"role": "user", "content":
                "ERROR: no valid ```tool block found. Emit EXACTLY ONE tool call in a ```tool fence "
                "(use `finish` if you have already verified your work)."})
            continue
        consecutive_bad = 0

        if call.name == "finish":
            # Self-verify before submitting (plan Part 2A): if it wrote an artifact but never ran/rendered/
            # saw it, nudge ONCE to verify. Advisory, not a hard block -- if it insists (or already
            # verified, or wrote nothing), the next finish is accepted.
            if wrote_files and not verified and not nudged_verify:
                nudged_verify = True
                messages.append({"role": "user", "content":
                    "[VERIFY] You wrote code but have not RUN or RENDERED it. Before finishing, verify it "
                    "actually works: use `run` (code) or `render` then `see` (a scene), read the result, and "
                    "fix any error. Then finish. Don't submit unverified work."})
                continue
            return AgentResult(State.DONE, steps, plan, messages, str(workspace), True)

        if call.name == "write_file":
            wrote_files = True
        elif call.name in ("run", "render", "see"):
            verified = True

        try:
            result = exec_tool(call, workspace, run_timeout=run_timeout, vision=vision,
                               notebook=notebook, render_fn=render_fn)
        except Exception as e:  # a tool raising (PermissionError, OSError, disk full, ...) is an
            # OBSERVATION, not a crash -- the whole agent run must not die because one file write failed.
            result = ToolResult(False, f"tool '{call.name}' errored: {type(e).__name__}: {e}")
        if result.ok:
            consecutive_errors = 0
            content = f"[{call.name}] OK\n{result.output}"
            # After a SUCCESSFUL verify (render/run), cue it once to finish if satisfied. Observed on gpt-oss:
            # it builds + renders a good scene but then never emits `finish` -- ending STUCK (prose) or
            # MAX_STEPS. This closes that out. Advisory + one-time; it can keep improving instead.
            if call.name in ("render", "run") and not hinted_finish:
                hinted_finish = True
                content += ("\n\n[DONE?] You have verified your work. If it satisfies the task, emit a "
                            "`finish` tool call now; otherwise keep improving it.")
            messages.append({"role": "user", "content": content})
        else:
            consecutive_errors += 1
            content = f"[{call.name}] ERROR\n{result.output}"
            if consecutive_errors >= 2:
                # Stubborn-but-creative re-plan trigger: banging the same wall is not persistence. Force a
                # diagnosis + a DIFFERENT approach instead of repeating the failing move or giving up.
                content += (f"\n\n[REPLAN] That has failed {consecutive_errors} times in a row. Do NOT "
                            "repeat the same call. In one line, state WHY it is failing; then take a "
                            "DIFFERENT approach — a different tool, method, or angle (re-read the exact "
                            "error, search the code/notebook, simplify, or verify a smaller piece). Keep "
                            "going until it works; do not finish on a failing state.")
            messages.append({"role": "user", "content": content})

    return AgentResult(State.MAX_STEPS, steps, plan, messages, str(workspace), False)
