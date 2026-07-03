"""Render a loose GDScript scene off-screen via the capture rig.

Feeds the visual side of the gate and Icarus's `see` tool: given a ``scene.gd`` (an ``extends
Node3D`` script that builds its scene in ``_ready``), copy it into the rig project and render one
frame off-screen to a PNG. ``image_variance`` gives the cheap blank/not-blank signal.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from game.godot.binary import godot_path

_REPO = Path(__file__).resolve().parents[2]
_RIG = _REPO / "tools" / "godot_capture"


def render_gdscript(scene_gd: Path, out_png: Path, *, size: str = "512x512",
                    timeout: float = 90.0) -> "tuple[bool, str]":
    """Render ``scene_gd`` to ``out_png`` off-screen. Returns (ok, detail); never raises."""
    godot = godot_path()
    if godot is None:
        return False, "godot not installed"
    scene_gd = Path(scene_gd)
    if not scene_gd.is_file():
        return False, f"no such script: {scene_gd}"
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    probe = _RIG / "_probe.gd"
    try:
        shutil.copyfile(scene_gd, probe)
        try:
            proc = subprocess.run(
                [godot, "--path", str(_RIG), "--",
                 "--script=res://_probe.gd", f"--out={out_png}", f"--size={size}"],
                capture_output=True, text=True, timeout=timeout)
        except Exception as e:  # subprocess/timeout — an observation, not a crash
            return False, f"render crashed: {e}"
        if not out_png.exists():
            tail = (proc.stderr or proc.stdout or "").strip()[-200:]
            return False, f"no PNG produced (rc={proc.returncode}): {tail}"
        # Surface the deterministic blank-detector so callers (and Icarus's render tool) get a
        # reliable "is it blank?" signal without trusting a weak vision model.
        try:
            var = image_variance(out_png)
            note = f"rendered; pixel variance {var:.1f}" + (" - BLANK/black!" if var < 6.0 else " (not blank)")
        except Exception:
            note = f"rendered (rc={proc.returncode})"
        return True, note
    finally:
        probe.unlink(missing_ok=True)


def image_variance(png: Path) -> float:
    """Max per-channel pixel std-dev (0 == blank). Requires Pillow (used across the gate)."""
    from PIL import Image, ImageStat
    return max(ImageStat.Stat(Image.open(png).convert("RGB")).stddev)
