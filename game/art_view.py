"""Render a pond STATE as ART -- composite the generated sprites (assets/art/) into the game view.

The real-art replacement for the primitive-mesh renderer (game/godot/pond_view.py). Given a game state, it
places each building's ART sprite (a painterly cozy-game illustration) at its isometric screen position, adds
a goose by each nest and trees around the edge, depth-sorted over a grass + pond background, and writes a
PNG. The game logic (geese-from-nests, placement, economy) is unchanged; only the LOOK is now real art.

Sprites come from ops/generate_art.py (free image model). Missing assets degrade gracefully to a soft
coloured placeholder so the view always renders (and improves as assets land).
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
ART_DIR = _REPO / "assets" / "art"

# on-screen sprite heights (px) per kind; buildings big, geese small, trees medium
_SIZES = {"bakery": 210, "granary": 200, "nest": 120, "well": 170, "fence": 130,
          "tree": 190, "goose": 120}
_GRASS = (126, 189, 100)
_POND = (86, 150, 196)
_TILE_W = 150   # isometric tile footprint on screen
_TILE_H = 86


def _load(name: str):
    """Load a sprite (prefer the transparent *_cutout.png), or None if absent."""
    from PIL import Image
    for fn in (f"{name}_cutout.png", f"{name}.png"):
        p = ART_DIR / fn
        if p.is_file():
            try:
                return Image.open(p).convert("RGBA")
            except Exception:  # noqa: BLE001 - a corrupt asset shouldn't break the render
                return None
    return None


def _scaled(name: str, target_h: int):
    im = _load(name)
    if im is None:
        return None
    w, h = im.size
    s = target_h / h
    return im.resize((max(1, int(w * s)), max(1, int(h * s)))) if s != 1 else im


def _placeholder(canvas, cx: int, by: int, kind: str) -> None:
    """A soft, semi-transparent tinted hint when an art asset isn't generated yet -- unobtrusive (blends
    into the scene) rather than a jarring solid blob, so a still-missing asset doesn't spoil the view."""
    from PIL import Image, ImageDraw
    col = {"bakery": (196, 120, 90), "granary": (200, 170, 120), "nest": (150, 110, 80),
           "well": (170, 175, 178), "fence": (150, 110, 80), "tree": (110, 160, 100),
           "goose": (245, 245, 240)}.get(kind, (170, 175, 178))
    r = _SIZES.get(kind, 120) // 3
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, by - r // 2, cx + r, by], fill=(60, 90, 55, 60))          # a soft ground shadow
    d.ellipse([cx - r, by - 2 * r, cx + r, by - r // 3], fill=col + (150,))       # a soft tinted mound
    canvas.alpha_composite(layer)


def compose_pond_art(state: dict, out_png: "str | Path", *, size: "tuple[int, int]" = (1200, 900)) -> Path:
    """Composite ``state`` into an art PNG at ``out_png``. Returns the path. Always renders."""
    from PIL import Image, ImageDraw
    W, H = size
    canvas = Image.new("RGBA", (W, H), _GRASS + (255,))

    ground = _load("ground")
    if ground is not None:
        canvas.paste(ground.resize((W, H)).convert("RGBA"), (0, 0))

    cx0, cy0 = W // 2, int(H * 0.46)                      # screen centre of the grid origin

    def screen(gx: float, gy: float) -> "tuple[int, int]":
        return (int(cx0 + (gx - gy) * _TILE_W / 2), int(cy0 + (gx + gy) * _TILE_H / 2))

    # pond: a big art sprite (or a soft blue diamond) centred
    pond = _scaled("pond", int(H * 0.34))
    if pond is not None:
        canvas.alpha_composite(pond, (cx0 - pond.width // 2, cy0 - pond.height // 3))
    else:
        # a hand-drawn cozy pond: grassy bank + water + ripple highlight + a few lily pads (reads as
        # intentional, not a placeholder; replaced by pond.png once it generates)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(layer)
        pw, ph = int(W * 0.30), int(H * 0.17)
        pd.ellipse([cx0 - pw // 2 - 9, cy0 - ph // 2 - 6, cx0 + pw // 2 + 9, cy0 + ph // 2 + 6],
                   fill=(86, 132, 74, 190))           # grassy bank
        pd.ellipse([cx0 - pw // 2, cy0 - ph // 2, cx0 + pw // 2, cy0 + ph // 2], fill=(92, 156, 202, 235))
        pd.ellipse([cx0 - pw // 2 + 12, cy0 - ph // 2 + 7, cx0 + pw // 2 - 12, cy0 - ph // 8],
                   fill=(156, 204, 232, 95))          # ripple highlight
        for lx, ly, lr in [(-0.30, 0.12, 15), (0.24, -0.14, 12), (0.06, 0.26, 13)]:
            px, py = cx0 + int(lx * pw), cy0 + int(ly * ph)
            pd.ellipse([px - lr, py - lr // 2, px + lr, py + lr // 2], fill=(96, 158, 82, 235))
            pd.ellipse([px - 3, py - 2, px + 3, py + 2], fill=(210, 120, 150, 210))   # a tiny flower
        canvas.alpha_composite(layer)

    buildings = state.get("buildings", [])
    xs = [b["x"] for b in buildings] or [0]
    ys = [b["y"] for b in buildings] or [0]
    ox, oy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0

    # collect drawables (kind, grid x, grid y) then paint back-to-front by depth = gx+gy
    items: "list[tuple[float, float, str]]" = []
    for b in buildings:
        items.append((b["x"] - ox, b["y"] - oy, b.get("kind", "")))
    for b in buildings:                                   # a goose beside each nest
        if b.get("kind") == "nest":
            items.append((b["x"] - ox + 0.45, b["y"] - oy + 0.2, "goose"))
    for gx, gy in [(-2.4, -2.4), (2.4, -2.4), (2.4, 2.4), (-2.4, 2.4)]:   # corner trees (on the island)
        items.append((gx, gy, "tree"))

    draw = ImageDraw.Draw(canvas)
    for gx, gy, kind in sorted(items, key=lambda t: t[0] + t[1]):
        sx, sy = screen(gx, gy)
        spr = _scaled(kind, _SIZES.get(kind, 120))
        if spr is not None:
            canvas.alpha_composite(spr, (sx - spr.width // 2, sy - spr.height))   # anchor at the feet
        else:
            _placeholder(canvas, sx, sy, kind)

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_png)
    return out_png
