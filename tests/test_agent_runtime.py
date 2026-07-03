"""Offline tests for Icarus' agent runtime (the plan->act->reflect loop).

Driven by a deterministic ScriptedAgentModel, so the loop + tool protocol + sandbox are proven
end-to-end with no Ollama/GPU. The live OllamaAgentModel is exercised separately.
"""

from __future__ import annotations

from harness.icarus.agent import (
    Notebook,
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


def test_run_tool_shows_the_error_at_the_end_of_long_output(tmp_path):
    # Icarus fixes what it can SEE: a Python traceback / Godot error is the LAST line, and stderr is
    # appended after stdout, so head-truncating long output hid the error. Tail-truncation must keep it.
    import sys
    from harness.icarus.agent.runtime import exec_tool, ToolCall
    (tmp_path / "prog.py").write_text("print('x' * 5000)\nraise ValueError('THE REAL ERROR')\n")
    res = exec_tool(ToolCall(name="run", args={"cmd": f"{sys.executable} prog.py"}, body=None),
                    tmp_path, run_timeout=20)
    assert res.ok is False
    assert "THE REAL ERROR" in res.output           # the error survived truncation
    assert "head truncated" in res.output            # and it was the head, not the error, that was dropped


def test_run_agent_injects_late_notebook_lessons(tmp_path):
    # harness-mod-53 proof: the WHOLE curated notebook reaches Icarus. Capture what the model receives and
    # assert a LATE lesson (the Godot-4 `.translation` rule, past the old 2000-char cap) is in the prompt.
    from harness.icarus.agent.runtime import run_agent, ScriptedAgentModel
    from game.godot.lessons import godot_notebook

    seen = {}

    class Capturing(ScriptedAgentModel):
        def complete(self, messages):
            seen.setdefault("messages", [dict(m) for m in messages])
            return super().complete(messages)

    model = Capturing(["```tool\nname: finish\nsummary: done\n```"])
    run_agent(model, "build a scene", tmp_path, notebook=godot_notebook(), use_notebook=True, max_steps=1)
    joined = "\n".join(m["content"] for m in seen["messages"])
    assert "NOTEBOOK" in joined                      # the notebook was injected
    assert "translation" in joined                   # ...including the late lesson the old cap dropped


def test_curated_notebook_fits_the_injection_cap():
    # run_agent injects nb[:_NOTEBOOK_CHAR_CAP]; if the curated seed exceeds it, later lessons are silently
    # cut from Icarus's prompt (that dropped the Godot-4 `.translation` rule -> the OP-35 bug). Guard it.
    from harness.icarus.agent.runtime import _NOTEBOOK_CHAR_CAP
    from game.godot.lessons import LESSONS_PATH
    seed = LESSONS_PATH.read_text(encoding="utf-8")
    assert "translation" in seed                          # the late lesson exists
    assert len(seed) <= _NOTEBOOK_CHAR_CAP, (
        f"curated notebook {len(seed)} chars > cap {_NOTEBOOK_CHAR_CAP}: later lessons would be truncated "
        "out of the prompt — raise _NOTEBOOK_CHAR_CAP or split the seed")


def test_repeated_failures_trigger_a_replan_nudge(tmp_path):
    # Persistence (Bridger's feedback): banging the same wall is not acceptable. After >=2 consecutive tool
    # ERRORs the loop must inject a [REPLAN] nudge forcing a different approach -- but not on the first miss.
    from harness.icarus.agent.runtime import run_agent, ScriptedAgentModel
    fail = "```tool\nname: read_file\npath: does_not_exist.txt\n```"
    model = ScriptedAgentModel([fail, fail, "```tool\nname: finish\nsummary: done\n```"])
    res = run_agent(model, "task", tmp_path, max_steps=5)
    obs = [m["content"] for m in res.transcript
           if m["role"] == "user" and m["content"].startswith("[read_file]")]
    assert len(obs) >= 2, obs
    assert "[REPLAN]" not in obs[0]          # first failure: just the error, no nagging
    assert "[REPLAN]" in obs[1]              # second consecutive failure: forced to try a different approach


def test_tool_exception_is_an_observation_not_a_crash(tmp_path, monkeypatch):
    # A tool raising (PermissionError from a locked file, disk full, any OSError) must NOT crash the whole
    # agent run -- it's an observation the agent reflects on. (A real place_n8 battery task crashed this way.)
    from pathlib import Path
    from harness.icarus.agent.runtime import run_agent, ScriptedAgentModel

    def boom(self, *a, **k):
        raise PermissionError("[Errno 13] Permission denied (simulated)")

    monkeypatch.setattr(Path, "write_text", boom)
    model = ScriptedAgentModel(["```tool\nname: write_file\npath: x.py\nbody:\nprint(1)\n```",
                                "```tool\nname: finish\nsummary: done\n```"])
    res = run_agent(model, "task", tmp_path, max_steps=3)   # must RETURN, not raise
    assert res.state.value in ("DONE", "MAX_STEPS", "STUCK")


def test_parse_is_crash_proof_on_garbage():
    # A local model can emit anything; the parser must never raise (a crash would derail the agent loop).
    for junk in ("", "```tool\n```", "```tool\n\x00\x01 random :: :\n```", "```tool\nname:\n```"):
        parse_tool_call(junk)  # just must not raise
    # a block with no name is not a usable call
    assert parse_tool_call("```tool\npath: x.py\n```") is None


def test_trim_context_keeps_setup_and_recent_bounds_growth():
    from harness.icarus.agent.runtime import _CONTEXT_KEEP_RECENT, _trim_context
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "TASK: do X"}]
    for i in range(10):
        msgs.append({"role": "assistant", "content": f"reply {i}"})
        msgs.append({"role": "user", "content": f"obs {i}"})
    trimmed = _trim_context(msgs, "my plan")
    assert trimmed[0]["content"] == "sys" and "do X" in trimmed[1]["content"]   # setup kept
    assert any("trimmed to save context" in m["content"] for m in trimmed)      # marker present
    assert trimmed[-1]["content"] == "obs 9"                                    # recent kept verbatim
    assert len(trimmed) <= 2 + 1 + _CONTEXT_KEEP_RECENT                          # growth bounded


def test_trim_context_keeps_the_notebook_across_a_long_run():
    # harness-mod-53's benefit must PERSIST: the notebook is an early setup message (before the first
    # assistant reply), so it lives in `head` and survives trimming -- Icarus keeps its lessons all run,
    # not just step 1. (If a refactor only kept system+task, the lessons would silently vanish after step 1.)
    from harness.icarus.agent.runtime import _trim_context
    msgs = [{"role": "system", "content": "sys"},
            {"role": "user", "content": "NOTEBOOK - lessons: use .position not .translation in Godot 4"},
            {"role": "user", "content": "TASK: build a scene"}]
    for i in range(12):
        msgs.append({"role": "assistant", "content": f"reply {i}"})
        msgs.append({"role": "user", "content": f"obs {i}"})
    joined = "\n".join(m["content"] for m in _trim_context(msgs, "plan"))
    assert "NOTEBOOK" in joined and "translation" in joined   # lessons still present after 12 steps


def test_trim_context_leaves_short_runs_untouched():
    from harness.icarus.agent.runtime import _trim_context
    short = [{"role": "system", "content": "s"}, {"role": "user", "content": "t"},
             {"role": "assistant", "content": "a"}, {"role": "user", "content": "o"}]
    assert _trim_context(short, "p") == short


def test_parse_recovers_unclosed_block():
    # model dropped the closing fence / output was truncated -> recover instead of wasting the turn
    txt = "I'll write it.\n```tool\nname: write_file\npath: a.py\nbody:\nprint(1)\n"
    call = parse_tool_call(txt)
    assert call is not None and call.name == "write_file"
    assert call.args["path"] == "a.py" and "print(1)" in call.body


def test_parse_prefers_closed_block_over_unclosed_tail():
    # a complete block still wins; the fallback only fires when there is no closed block
    txt = "```tool\nname: finish\nsummary: done\n```\nthen ```tool\nname: write_file\n"
    call = parse_tool_call(txt)
    assert call is not None and call.name == "finish"


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


class _ExplodingModel:
    def complete(self, messages):
        raise RuntimeError("boom (simulated model/network failure)")


def test_model_failure_degrades_to_stuck_not_crash(tmp_path):
    # A model/network failure (e.g. a transient Ollama 500) must not crash the loop.
    res = run_agent(_ExplodingModel(), "task", tmp_path, max_steps=5)
    assert res.state == State.STUCK


def test_unknown_tool_is_error_not_crash(tmp_path):
    r = exec_tool(ToolCall("frobnicate", {}), tmp_path)
    assert not r.ok
    assert "unknown tool" in r.output.lower()


def test_list_files(tmp_path):
    (tmp_path / "a.py").write_text("print('hi')\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("x\n")
    r = exec_tool(ToolCall("list_files", {}), tmp_path)
    assert r.ok
    assert "a.py" in r.output
    assert "sub/b.txt" in r.output


def test_search_finds_and_misses(tmp_path):
    (tmp_path / "a.py").write_text("import os\nx = NEEDLE + 1\n")
    hit = exec_tool(ToolCall("search", {"query": "NEEDLE"}), tmp_path)
    assert hit.ok
    assert "a.py:2" in hit.output and "NEEDLE" in hit.output
    miss = exec_tool(ToolCall("search", {"query": "zzz_no_match"}), tmp_path)
    assert miss.ok and "no matches" in miss.output


def test_search_bad_regex_falls_back_to_literal(tmp_path):
    (tmp_path / "a.txt").write_text("value = a[b unclosed\n")
    r = exec_tool(ToolCall("search", {"query": "a[b"}), tmp_path)  # invalid regex -> literal match
    assert r.ok and "a.txt" in r.output


class _StubVision:
    def describe(self, image_path, question):
        return f"A green hexagon on gray. (asked: {question})"


def test_see_uses_vision(tmp_path):
    (tmp_path / "img.png").write_bytes(b"\x89PNGfake")
    r = exec_tool(ToolCall("see", {"path": "img.png", "question": "what shape?"}),
                  tmp_path, vision=_StubVision())
    assert r.ok
    assert "green hexagon" in r.output.lower()
    assert "what shape?" in r.output


def test_see_disabled_without_vision(tmp_path):
    (tmp_path / "img.png").write_bytes(b"x")
    r = exec_tool(ToolCall("see", {"path": "img.png"}), tmp_path)
    assert not r.ok and "vision" in r.output.lower()


def test_see_missing_image(tmp_path):
    r = exec_tool(ToolCall("see", {"path": "nope.png"}), tmp_path, vision=_StubVision())
    assert not r.ok


def test_render_tool_uses_render_fn(tmp_path):
    (tmp_path / "scene.gd").write_text("extends Node3D\n")
    calls = []

    def fake_render(src, out):
        calls.append((src, out))
        out.write_bytes(b"png")
        return True, "rendered (variance 40)"

    r = exec_tool(ToolCall("render", {"path": "scene.gd", "out": "p.png"}), tmp_path,
                  render_fn=fake_render)
    assert r.ok
    assert "see" in r.output.lower()
    assert calls and calls[0][0].name == "scene.gd"


def test_render_tool_disabled_without_fn(tmp_path):
    (tmp_path / "scene.gd").write_text("x")
    r = exec_tool(ToolCall("render", {"path": "scene.gd"}), tmp_path)
    assert not r.ok and "renderer" in r.output.lower()


def test_render_tool_missing_file(tmp_path):
    r = exec_tool(ToolCall("render", {"path": "nope.gd"}), tmp_path, render_fn=lambda s, o: (True, ""))
    assert not r.ok


def test_notebook_append_and_dedup(tmp_path):
    nb = Notebook(tmp_path / "nb.md")
    assert nb.append("look_at requires a node in the tree before calling it")
    assert not nb.append("look_at requires a node in the tree before calling it")  # dup
    assert not nb.append("   ")  # empty
    assert len(nb.entries()) == 1


def test_note_tool_saves_to_notebook(tmp_path):
    nb = Notebook(tmp_path / "nb.md")
    r = exec_tool(ToolCall("note", {"text": "always run code before finishing"}),
                  tmp_path, notebook=nb)
    assert r.ok and "saved" in r.output.lower()
    assert "always run code" in nb.read()


def test_note_ephemeral_without_notebook(tmp_path):
    r = exec_tool(ToolCall("note", {"text": "x"}), tmp_path)
    assert r.ok and "ephemeral" in r.output.lower()


def test_run_agent_injects_notebook_unless_stripped(tmp_path):
    nb = Notebook(tmp_path / "nb.md")
    nb.append("REMEMBER-THIS-LESSON about geese")
    replies = ['```tool\nname: finish\nsummary: done\n```']
    res = run_agent(ScriptedAgentModel(replies), "task", tmp_path, notebook=nb, use_notebook=True)
    joined = "\n".join(m["content"] for m in res.transcript)
    assert "REMEMBER-THIS-LESSON" in joined
    # strip-to-test: disabling the notebook removes the injected memory
    res2 = run_agent(ScriptedAgentModel(replies), "task", tmp_path, notebook=nb, use_notebook=False)
    joined2 = "\n".join(m["content"] for m in res2.transcript)
    assert "REMEMBER-THIS-LESSON" not in joined2


def _tool(*rows):
    nl = chr(10)
    return "```tool" + nl + nl.join(rows) + nl + "```"


def test_finish_without_verifying_gets_a_one_time_nudge(tmp_path):
    # Self-verify (plan Part 2A): finishing right after writing code, with no run/render, is nudged ONCE.
    from harness.icarus.agent.runtime import run_agent, ScriptedAgentModel, State
    w = _tool("name: write_file", "path: a.py", "body:", "print(1)")
    fin = _tool("name: finish", "summary: done")
    res = run_agent(ScriptedAgentModel([w, fin, fin]), "task", tmp_path, max_steps=5)
    nudges = [m for m in res.transcript if m["role"] == "user" and "[VERIFY]" in m["content"]]
    assert len(nudges) == 1
    assert res.state == State.DONE


def test_finish_after_verifying_is_not_nudged(tmp_path):
    # wrote then RAN -> already verified -> finish accepted immediately, no nudge.
    from harness.icarus.agent.runtime import run_agent, ScriptedAgentModel, State
    w = _tool("name: write_file", "path: a.py", "body:", "print(1)")
    run = _tool("name: run", "cmd: python a.py")
    fin = _tool("name: finish", "summary: done")
    res = run_agent(ScriptedAgentModel([w, run, fin]), "task", tmp_path, max_steps=5)
    assert not any("[VERIFY]" in m["content"] for m in res.transcript if m["role"] == "user")
    assert res.state == State.DONE
