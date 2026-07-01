"""The One Pond screenshot seam — how the visual gate sees the game.

The Phase-0 finding was that Godot ``--headless`` disables rendering, so real screenshots need
Godot under a virtual framebuffer (Xvfb). Rather than block Phase 4 on that, rendering is a
swappable ``ScreenshotWorker``:

* ``StubScreenshotWorker`` — deterministic top-down render of a config with Pillow, no Godot.
  Enough for the visual gate to score composition/among-building layout and for the pipeline to
  run today.
* ``GodotXvfbWorker`` — the real seam: launch the Godot project under Xvfb at the fixed
  ``iso_camera.json`` and grab the framebuffer. Lazily invoked; documented, not unit-tested
  here because no Godot binary is present.

Either way the output is a PNG the same ``ReferenceAnchoredScorer`` used in Stage B can judge,
so "the visual gate sees the game" is true now (stub) and stays true after the Godot swap.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Protocol, runtime_checkable

from game.onepond.world import build_world

# Building -> fill colour for the stub render (roughly the low-poly palette).
_TILE = {
    "bakery": (210, 180, 140),
    "hatchery": (139, 69, 19),
    "granary": (150, 150, 160),
}
_POND = (34, 139, 34)
_GRID_LINE = (24, 100, 24)


@runtime_checkable
class ScreenshotWorker(Protocol):
    id: str

    def render(self, config: dict, out_path: Path) -> Path: ...


class StubScreenshotWorker(ScreenshotWorker):
    """Deterministic top-down pond render (no Godot). Good enough to exercise the visual gate."""

    id = "stub-screenshot"

    def __init__(self, tile_px: int = 14, margin: int = 8):
        self.tile_px = tile_px
        self.margin = margin

    def render(self, config: dict, out_path: Path) -> Path:
        from PIL import Image, ImageDraw

        world = build_world(config)  # validates the layout as a side benefit
        gw, gh = world.grid_w, world.grid_h
        w = self.margin * 2 + gw * self.tile_px
        h = self.margin * 2 + gh * self.tile_px
        im = Image.new("RGB", (w, h), _POND)
        d = ImageDraw.Draw(im)
        for i in range(gw + 1):  # grid lines give the render real edge structure
            x = self.margin + i * self.tile_px
            d.line([(x, self.margin), (x, self.margin + gh * self.tile_px)], fill=_GRID_LINE)
        for j in range(gh + 1):
            y = self.margin + j * self.tile_px
            d.line([(self.margin, y), (self.margin + gw * self.tile_px, y)], fill=_GRID_LINE)
        for b in world.buildings:
            x0 = self.margin + b.x * self.tile_px + 2
            y0 = self.margin + b.y * self.tile_px + 2
            d.rectangle([x0, y0, x0 + self.tile_px - 4, y0 + self.tile_px - 4],
                        fill=_TILE.get(b.type, (200, 200, 200)), outline=(60, 40, 20))
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(out_path)
        return out_path


class GodotXvfbWorker(ScreenshotWorker):  # pragma: no cover - requires a Godot binary + Xvfb
    """Real render seam: Godot under Xvfb at the fixed iso camera. Not run in the test suite."""

    id = "godot-xvfb"

    def __init__(self, godot_bin: str, project_dir: Path, scene: str = "res://OnePond.tscn"):
        self.godot_bin = godot_bin
        self.project_dir = Path(project_dir)
        self.scene = scene

    def render(self, config: dict, out_path: Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        (self.project_dir / "run_config.json").write_text(json.dumps(config))
        # NOTE: real invocation runs Godot under a virtual framebuffer, e.g.:
        #   xvfb-run -a godot --path <project> --render-onepond <config> --screenshot <out>
        subprocess.run(
            ["xvfb-run", "-a", self.godot_bin, "--path", str(self.project_dir),
             "--screenshot", str(out_path), self.scene],
            check=True, capture_output=True,
        )
        return out_path
