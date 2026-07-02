"""Godot engine integration for the GGG gate: binary location + deterministic checks.

The capture rig itself lives in ``tools/godot_capture/`` (a small Godot project that renders
an arbitrary scene off-screen to a PNG). This package is the Python side: locating the Godot
binary and the certified ``Check``s that gate GDScript/scenes Icarus produces.
"""
