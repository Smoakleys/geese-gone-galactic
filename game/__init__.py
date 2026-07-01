"""Geese Gone Galactic — the game. Phase 4 target: "One Pond".

The Python packages here are the *authoritative* game model (world, bread economy, placement,
save/load). Godot/GDScript is a thin view over this model; keeping the logic in Python means
the harness can build, gate, and regression-test the whole game deterministically without a
Godot binary. See ``game/README.md`` for the Godot/screenshot seam.
"""
