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
        # Surface an honest "did the scene actually render content?" signal. Two failure modes:
        #   * near-BLACK  (camera saw nothing)                     -> brightest channel ~0
        #   * uniform GRAY (only the default background, no scene) -> R~=G~=B (no colour)
        # A real render has a coloured region, so it is neither near-black nor near-uniform.
        try:
            r, g, b = channel_means(out_png)
            empty = max(r, g, b) < BLANK_FLOOR or (abs(r - g) < 8 and abs(g - b) < 8 and abs(r - b) < 8)
            note = (f"rendered; mean RGB=({r:.0f},{g:.0f},{b:.0f})"
                    + (" - looks EMPTY (uniform background; no scene content visible)" if empty else ""))
        except Exception:
            note = f"rendered (rc={proc.returncode})"
        return True, note
    finally:
        probe.unlink(missing_ok=True)


BLANK_FLOOR = 20.0  # brightest-channel mean below this == a near-black (failed) render


def channel_means(png: Path) -> "tuple[float, float, float]":
    """Per-channel (R,G,B) pixel means. Requires Pillow."""
    from PIL import Image, ImageStat
    m = ImageStat.Stat(Image.open(png).convert("RGB")).mean
    return m[0], m[1], m[2]


def green_dominance(png: Path) -> float:
    """How much greener than red/blue the render is. ~0 for gray/empty or black; high for a green
    scene. The honest 'the green plane actually rendered' signal (a gray background scores ~0)."""
    r, g, b = channel_means(png)
    return g - max(r, b)


def image_variance(png: Path) -> float:
    """Max per-channel pixel std-dev (a 'has structure' signal, distinct from blank/not-blank)."""
    from PIL import Image, ImageStat
    return max(ImageStat.Stat(Image.open(png).convert("RGB")).stddev)


def color_fraction(png: Path, kind: str, margin: int = 20) -> float:
    """Fraction of pixels where the ``kind`` channel ('red'|'green'|'blue') strictly dominates the other
    two by ``margin``. Region-based on purpose: channel MEANS wash out in a multi-terrain scene (green
    land + a blue pond in one frame average to muddy grey), but per-pixel dominance still finds each
    region. Grey background and equal-channel pixels count for nothing."""
    from PIL import Image
    idx = {"red": 0, "green": 1, "blue": 2}[kind]
    a, b = (idx + 1) % 3, (idx + 2) % 3
    im = Image.open(png).convert("RGB")
    total = im.width * im.height
    data = im.tobytes()
    hits = sum(1 for i in range(0, len(data), 3)
               if data[i + idx] > max(data[i + a], data[i + b]) + margin)
    return hits / total if total else 0.0


def significant_colors(png: Path, min_fraction: float = 0.02, quant: int = 48) -> int:
    """Count distinct (coarsely-quantised) colours each covering >= ``min_fraction`` of the image.

    A flat fill is 1; a ground plane on the default background is 2; a ground WITH a distinctly-coloured
    building on it is 3+. The deterministic 'the scene has more than just the ground' signal that gates
    multi-object renders (e.g. a bakery box on the pond).

    ``min_fraction`` is 0.02: a building seen at an iso angle can occupy only ~3% of the frame, and 0.04
    wrongly failed a real, clearly-visible bakery box (found by looking at the render — the gate was
    too strict, not the builder)."""
    from collections import Counter

    from PIL import Image
    im = Image.open(png).convert("RGB")
    total = im.width * im.height
    data = im.tobytes()  # raw RGB bytes (getdata() is deprecated in Pillow 14)
    counts = Counter((data[i] // quant, data[i + 1] // quant, data[i + 2] // quant)
                     for i in range(0, len(data), 3))
    return sum(1 for n in counts.values() if n >= min_fraction * total)
