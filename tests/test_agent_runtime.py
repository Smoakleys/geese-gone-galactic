"""Offline tests for Icarus' agent runtime (the plan->act->reflect loop).

Driven by a deterministic ScriptedAgentModel, so the loop + tool protocol + sandbox are proven
end-to-end with no Ollama/GPU. The live OllamaAgentModel is exercised separately.
"""

from __future__ import annotations

from harness.icarus.agent import (
    ScriptedAgentModel,
    State,
    ToolCall,
    exec_tool,
    parse_tool_call,
    run_agent,
)


def test_parse_tool_call_multiline_body():
    txt = "reasoning\n```tool\nname: write_file\npath: a.txt\nbody:\nline1\nline2\n```\ntrailing"
    call = parse_tool_call(txt)
    assert call is not None
    assert call.name == "write_file"
    assert call.args["path"] == "a.txt"
    assert call.body == "line1\nline2"


def test_parse_takes_last_block():
    txt = "```tool\nname: read_file\npath: x\n```\n```tool\nname: finish\nsummary: done\n```"
    call = parse_tool_call(txt)
    assert call is not None and call.name == "finish"


def test_parse_none_when_no_block():
    assert parse_tool_call("no tool here") is None


def test_write_then_run_to_finish(tmp_path):
    replies = [
        'PLAN: write hello.py then run it.\n```tool\nname: write_file\npath: hello.py\nbody:\nprint("HELLO")\n```',
        'Run it to verify.\n```tool\nname: run\ncmd: python hello.py\n```',
        'Output verified.\n```tool\nname: finish\nsummary: printed HELLO\n```',
    ]
    res = run_agent(ScriptedAgentModel(replies), "Make hello.py print HELLO and run it.",
                    tmp_path, max_steps=6)
    assert res.state == State.DONE
    assert res.finished
    assert (tmp_path / "hello.py").exists()
    assert "HELLO" in (tmp_path / "hello.py").read_text()
    assert res.plan.startswith("PLAN")


def test_run_reports_failure(tmp_path):
    r = exec_tool(ToolCall("run", {"cmd": 'python -c "import sys; sys.exit(3)"'}), tmp_path)
    assert not r.ok
    assert "exit=3" in r.output


def test_write_file_sandbox_escape_blocked(tmp_path):
    r = exec_tool(ToolCall("write_file", {"path": "../escape.txt"}, body="x"), tmp_path)
    assert not r.ok
    assert "escape" in r.output.lower()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_stuck_after_repeated_bad_output(tmp_path):
    res = run_agent(ScriptedAgentModel(["no tool", "still nothing", "nope"]),
                    "task", tmp_path, max_steps=6)
    assert res.state == State.STUCK


def test_unknown_tool_is_error_not_crash(tmp_path):
    r = exec_tool(ToolCall("frobnicate", {}), tmp_path)
    assert not r.ok
    assert "unknown tool" in r.output.lower()
