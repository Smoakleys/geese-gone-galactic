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
        # Surface a reliable "is it blank?" signal. BLANK means near-BLACK (the camera saw nothing) -
        # NOT "uniform colour": a plane that fills the frame is a solid bright colour with ~0 variance
        # yet is a perfectly good render. So the blank-detector is brightness, not variance.
        try:
            b = brightest_mean(out_png)
            note = f"rendered; brightness {b:.0f}" + (" - BLANK/black!" if b < BLANK_FLOOR else " (not blank)")
        except Exception:
            note = f"rendered (rc={proc.returncode})"
        return True, note
    finally:
        probe.unlink(missing_ok=True)


BLANK_FLOOR = 20.0  # brightest-channel mean below this == a near-black (failed) render


def brightest_mean(png: Path) -> float:
    """Mean of the brightest RGB channel (0 == pure black). A solid bright colour scores high, so a
    valid full-frame render passes; only a near-black/empty render fails. Requires Pillow."""
    from PIL import Image, ImageStat
    return max(ImageStat.Stat(Image.open(png).convert("RGB")).mean)


def image_variance(png: Path) -> float:
    """Max per-channel pixel std-dev (a 'has structure' signal, distinct from blank/not-blank)."""
    from PIL import Image, ImageStat
    return max(ImageStat.Stat(Image.open(png).convert("RGB")).stddev)
