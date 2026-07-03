"""Generate the game's ART ASSETS with a free text-to-image model (Pollinations; no key).

Bridger's call (2026-07-03): the primitive-mesh look is "shapes, not art." This is the real-art pipeline:
each One Pond prop is a painterly cozy-game illustration in one coherent style, generated for free and
committed to ``assets/art/``. The game's visual layer composites these sprites by state (see
``game/art_view.py``) instead of assembling boxes and spheres.

Usage:
    python ops/generate_art.py                 # generate any missing assets (idempotent)
    python ops/generate_art.py --force         # regenerate all
    python ops/generate_art.py --only goose bakery
    python ops/generate_art.py --cutout        # also write *_cutout.png (white background -> transparent)

Free + flaky: requests are retried with backoff. Assets are committed so the game never needs regeneration.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
ART_DIR = _REPO / "assets" / "art"

# One coherent style so the whole game matches.
STYLE = (", cute cozy mobile game asset, soft painterly cartoon illustration, warm cheerful colors, "
         "centered single object, plain solid white background, high detail, no text")

# The game's props (keys match game/pond building kinds + goose/tree/scenery).
ASSETS: "dict[str, str]" = {
    "goose": "a plump friendly white cartoon goose with a bright orange beak, side view",
    "bakery": "a cozy little storybook bakery cottage with a warm red shingled roof and a chimney",
    "granary": "a round wooden grain silo barn with a domed roof",
    "nest": "a cozy twig bird nest with three white eggs",
    "well": "a charming round stone water well with a little wooden shingled roof",
    "fence": "a short section of rustic wooden fence with two posts and a rail",
    "tree": "a single round lush green tree with a sturdy brown trunk",
    "pond": "a small round pond of calm blue water seen from above, lily pads",
    "ground": "a seamless top-down patch of lush green grass, cozy game terrain, soft painterly",
}


def _url(prompt: str, seed: int, w: int, h: int) -> str:
    return ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + STYLE)
            + f"?width={w}&height={h}&nologo=true&model=flux&seed={seed}")


def fetch(prompt: str, seed: int, *, w: int = 640, h: int = 640, retries: int = 4) -> bytes:
    """Fetch one image, retrying the flaky free endpoint with backoff. Raises on final failure."""
    last: Exception = RuntimeError("no attempt")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(_url(prompt, seed, w, h), headers={"User-Agent": "ggg-art"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) > 2000:                       # a real image, not an error stub
                return data
            last = RuntimeError(f"tiny response ({len(data)}b)")
        except Exception as e:  # noqa: BLE001 - the endpoint 500s/timeouts under load; back off + retry
            last = e
        time.sleep(4 * (attempt + 1))
    raise last


def cutout(png_bytes: bytes, tol: int = 26) -> bytes:
    """White-background -> transparent, by flood-filling from the border. Best-effort for sprites on white."""
    import io
    from collections import deque
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    px = im.load()
    w, h = im.size
    seen = bytearray(w * h)
    dq: deque = deque()
    for x in range(w):
        for y in (0, h - 1):
            dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            dq.append((x, y))
    while dq:
        x, y = dq.pop()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, a = px[x, y]
        if r >= 255 - tol and g >= 255 - tol and b >= 255 - tol:   # near-white -> clear + spread
            px[x, y] = (r, g, b, 0)
            if x > 0: dq.append((x - 1, y))
            if x < w - 1: dq.append((x + 1, y))
            if y > 0: dq.append((x, y - 1))
            if y < h - 1: dq.append((x, y + 1))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def generate(names: "list[str]", *, force: bool = False, make_cutout: bool = False) -> "list[str]":
    ART_DIR.mkdir(parents=True, exist_ok=True)
    done: "list[str]" = []
    for i, name in enumerate(names):
        dst = ART_DIR / f"{name}.png"
        if dst.exists() and not force:
            print(f"{name}: exists (skip)")
            done.append(name)
            continue
        try:
            big = name in ("ground", "pond")
            data = fetch(ASSETS[name], seed=42 + i, w=(768 if big else 640), h=(512 if big else 640))
            dst.write_bytes(data)
            if make_cutout and name not in ("ground", "pond"):
                (ART_DIR / f"{name}_cutout.png").write_bytes(cutout(data))
            print(f"{name}: {len(data)} bytes OK")
            done.append(name)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: FAILED after retries ({type(e).__name__})")
        time.sleep(3)
    return done


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cutout", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args(argv)
    names = args.only or list(ASSETS)
    bad = [n for n in names if n not in ASSETS]
    if bad:
        print(f"unknown assets: {bad}; known: {list(ASSETS)}")
        return 2
    got = generate(names, force=args.force, make_cutout=args.cutout)
    print(f"\ngenerated/present {len(got)}/{len(names)} -> {ART_DIR}")
    return 0 if len(got) == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
