"""The assembled GGG Icarus builder — one factory wiring together everything the agent needs.

Combines the pieces built this session into the standard `AgentBuilder` the harness/autopilot drives:
  * model routing (visual/render/Godot tickets -> a 30B that renders 3/3; logic/code -> fast gpt-oss:20b)
  * the Godot render tool (so Icarus can turn a scene into a PNG)
  * the local vision model (so Icarus can `see` an image)
  * a working copy of the curated Godot lessons notebook (append-safe; the seed is never polluted)

`default_icarus_builder(workdir)` is the one call that gives you a fully-equipped Icarus.
"""

from __future__ import annotations

from pathlib import Path

from game.godot.capture import render_gdscript
from game.godot.lessons import godot_working_notebook
from game.godot.scene_template import materialize_templated_scene
from harness.icarus.agent.ollama import OllamaAgentModel
from harness.icarus.agent.vision import OllamaVisionModel
from harness.icarus.agent_builder import AgentBuilder, visual_router


def default_icarus_builder(workdir, *, fast: str = "gpt-oss:20b", big: str = "qwen3:30b",
                           max_steps: int = 10, run_timeout: float = 90.0) -> AgentBuilder:
    """A fully-equipped Icarus: routing + render tool + vision + curated Godot notebook (working copy).

    max_steps=10: every successful build measured finished within ~4-6 steps; a lower cap bounds the
    worst-case grind on the slow offloaded 30B (a failing build stops sooner and escalates) without
    affecting builds that succeed. Part of the speed pass."""
    workdir = Path(workdir)
    return AgentBuilder(
        router=visual_router(OllamaAgentModel(fast, temperature=0.2),
                             OllamaAgentModel(big, temperature=0.2)),
        vision=OllamaVisionModel(),
        notebook=godot_working_notebook(workdir),
        render_fn=render_gdscript,
        post_build=materialize_templated_scene,   # compose templated content.gd -> scene.gd before gating
        max_steps=max_steps, run_timeout=run_timeout)
