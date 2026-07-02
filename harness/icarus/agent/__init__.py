"""Icarus' agent runtime — the plan->act->reflect loop that turns a one-shot local model
into an autonomous agent (tools, observation, self-correction). This is 'Icarus' harness'
(distinct from the gate): the scaffolding I build up so Icarus can figure things out itself.
"""

from harness.icarus.agent.runtime import (
    AgentModel,
    AgentResult,
    ScriptedAgentModel,
    State,
    ToolCall,
    ToolResult,
    VisionModel,
    exec_tool,
    parse_tool_call,
    run_agent,
)

__all__ = [
    "AgentModel",
    "AgentResult",
    "ScriptedAgentModel",
    "State",
    "ToolCall",
    "ToolResult",
    "VisionModel",
    "exec_tool",
    "parse_tool_call",
    "run_agent",
]
