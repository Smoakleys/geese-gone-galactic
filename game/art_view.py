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


def _placeholder(draw, cx: int, by: int, kind: str) -> None:
    """A soft coloured blob when an art asset isn't generated yet (keeps the view renderable)."""
    col = {"bakery": (196, 90, 70), "granary": (210, 170, 110), "nest": (120, 80, 50),
           "well": (150, 150, 150), "fence": (140, 92, 56), "tree": (80, 140, 70),
           "goose": (245, 245, 240)}.get(kind, (180, 180, 180))
    r = _SIZES.get(kind, 120) // 3
    draw.ellipse([cx - r, by - 2 * r, cx + r, by], fill=col)


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
    pond = _scaled("pond", int(H * 0.42))
    if pond is not None:
        canvas.alpha_composite(pond, (cx0 - pond.width // 2, cy0 - pond.height // 3))
    else:
        d = ImageDraw.Draw(canvas)
        pw, ph = int(W * 0.42), int(H * 0.26)
        d.polygon([(cx0, cy0 - ph // 2), (cx0 + pw // 2, cy0), (cx0, cy0 + ph // 2), (cx0 - pw // 2, cy0)],
                  fill=_POND + (255,))

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
    for gx, gy in [(-3.2, -3.2), (3.2, -3.2), (3.2, 3.2), (-3.2, 3.2)]:   # corner trees
        items.append((gx, gy, "tree"))

    draw = ImageDraw.Draw(canvas)
    for gx, gy, kind in sorted(items, key=lambda t: t[0] + t[1]):
        sx, sy = screen(gx, gy)
        spr = _scaled(kind, _SIZES.get(kind, 120))
        if spr is not None:
            canvas.alpha_composite(spr, (sx - spr.width // 2, sy - spr.height))   # anchor at the feet
        else:
            _placeholder(draw, sx, sy, kind)

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_png)
    return out_png
