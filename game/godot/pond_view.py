"""Render an actual pond STATE to a lit 3D image — the logic→visual bridge, packaged.

The two halves of the game were built separately: `game/pond` is the simulation (a state = bread +
buildings). This connects them to the shared low-poly MODEL library (`game/godot/models.py`): each placed
building becomes its modelled prop (a roofed bakery, a silo granary, a nest with eggs, a well, a fence),
each nest gets a goose beside it, and it's composed on grass + a pond with a lit iso camera. So a PLAYED
game — the state you actually reached — is SEEN with the same cozy look as the authored scenes, not as
coloured cubes. The footprint is centred so the fixed camera frames ANY played state.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from game.godot.capture import render_gdscript
from game.godot import models as M


# World units per grid cell: wide enough that props (~1.6) sit apart, tight enough that the framed pond +
# buildings each stay a visible fraction of the render (the gate needs >= 3 distinct colours).
_SPACING = 2.2


def _footprint_center(buildings: "list[dict]") -> "tuple[float, float]":
    """World-coord centre of the buildings' footprint (grid x -> world x*_SPACING). The fixed camera frames
    the ORIGIN, so centring the footprint there keeps buildings on the land, not floating off."""
    if not buildings:
        return 0.0, 0.0
    xs = [b["x"] * _SPACING for b in buildings]
    zs = [b["y"] * _SPACING for b in buildings]
    return (min(xs) + max(xs)) / 2.0, (min(zs) + max(zs)) / 2.0


def pond_state_to_scene_gd(state: dict) -> str:
    """Compose a full lit ``scene.gd`` that renders ``state``'s buildings (as modelled props) + a goose by
    each nest on grass + a pond, footprint-centred + framed so the camera fits ANY played state."""
    buildings = state.get("buildings", [])
    ox, oz = _footprint_center(buildings)
    span = 0.0
    body = [
        "    var grass := PlaneMesh.new()", "    grass.size = Vector2(40, 40)",
        f"    _part(root, grass, {M.GRASS}, Vector3(0, 0, 0))",
        "    var pond := PlaneMesh.new()", "    pond.size = Vector2(7, 7)",
        f"    _part(root, pond, {M.POND}, Vector3(0, 0.02, 0))",
    ]
    for b in buildings:
        wx, wz = b["x"] * _SPACING - ox, b["y"] * _SPACING - oz    # footprint-centred world position
        span = max(span, abs(wx), abs(wz))
        body += M.building_lines(b.get("kind", ""), (wx, 0.0, wz))
    for b in buildings:                                       # a goose beside each nest (geese live there)
        if b.get("kind") == "nest":
            wx, wz = b["x"] * _SPACING - ox + 1.2, b["y"] * _SPACING - oz
            body += M.goose_lines((wx, 0.0, wz), s=0.45, face=-1)
    cam_size = max(9.0, span * 1.4 + 4.0)                     # tight frame: props stay a visible fraction
    return M.compose_model_scene(body, cam_target=(0, 0.8, 0), cam_size=cam_size)


def render_pond_state(state: dict, out_png: "str | Path") -> "tuple[bool, str]":
    """Render a pond ``state`` to ``out_png`` as a lit 3D scene. Returns (ok, detail); never raises."""
    scene = pond_state_to_scene_gd(state)
    work = Path(tempfile.mkdtemp(prefix="pond_view_"))
    gd = work / "scene.gd"
    gd.write_text(scene, encoding="utf-8")
    return render_gdscript(gd, Path(out_png))
