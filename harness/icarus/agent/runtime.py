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
        return None
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


def exec_tool(call: ToolCall, workspace: Path, *, run_timeout: float = 60.0) -> ToolResult:
    """Execute one tool call in the sandboxed workspace. Never raises — a tool failure is an
    observation the agent reflects on, not a crash."""
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
        tail = (proc.stdout or "")
        if proc.stderr:
            tail += "\n[stderr]\n" + proc.stderr
        return ToolResult(proc.returncode == 0, f"exit={proc.returncode}\n{tail.strip()[:_MAX_OUTPUT]}")

    return ToolResult(False, f"unknown tool: {name!r} (use write_file|read_file|run|finish)")


# ---------------------------------------------------------------- model seam

@runtime_checkable
class AgentModel(Protocol):
    """Chat seam: given the running message list, return the model's next reply."""
    def complete(self, messages: list[dict[str, str]]) -> str: ...


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

Respond with EXACTLY ONE fenced tool block and NOTHING ELSE (no prose outside the block):
```tool
name: <write_file|read_file|run|finish>
path: <relative path>      # write_file / read_file
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


def run_agent(model: AgentModel, task: str, workspace: Path, *,
              max_steps: int = 12, run_timeout: float = 60.0) -> AgentResult:
    """Drive the plan->act->reflect loop until the agent finishes, gets stuck, or runs out of steps.

    Returns an :class:`AgentResult` including the stated plan (the approach artifact) and the full
    transcript (the trajectory the fresh critic and the scorecard can inspect)."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"TASK:\n{task}\n\nEmit your first tool call now."},
    ]
    plan = ""
    consecutive_bad = 0
    steps = 0
    for steps in range(1, max_steps + 1):
        reply = model.complete(messages)
        messages.append({"role": "assistant", "content": reply})
        if not plan:
            plan = _extract_plan(reply)

        call = parse_tool_call(reply)
        if call is None:
            consecutive_bad += 1
            if consecutive_bad >= 3:
                return AgentResult(State.STUCK, steps, plan, messages, str(workspace), False)
            messages.append({"role": "user", "content":
                "ERROR: no valid ```tool block found. Emit EXACTLY ONE tool call in a ```tool fence."})
            continue
        consecutive_bad = 0

        if call.name == "finish":
            return AgentResult(State.DONE, steps, plan, messages, str(workspace), True)

        result = exec_tool(call, workspace, run_timeout=run_timeout)
        status = "OK" if result.ok else "ERROR"
        messages.append({"role": "user", "content": f"[{call.name}] {status}\n{result.output}"})

    return AgentResult(State.MAX_STEPS, steps, plan, messages, str(workspace), False)
