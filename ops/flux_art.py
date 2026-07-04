"""Generate the game's art with FLUX via Pollinations — FREE and KEYLESS (no signup/approval).

Bridger's rule (memory never-wait-route-around-approval): never wait on him for a key. Google gates its good
image model behind a key, but Pollinations serves FLUX with no key at all — just slower/rate-limited, which
we handle with patient spacing + backoff. Flux produces genuinely good cozy-game art (a Hay Day / Cozy Grove
look). This module LOCKS one isometric viewpoint across every asset (the fix for "wrong viewpoints") + cuts
the background to transparency, and writes assets/art/flux_<name>.png (which game/art_view prefers).

Usage:
    python ops/flux_art.py                 # generate all assets + a reference + a review contact sheet
    python ops/flux_art.py --only goose    # regenerate specific props (e.g. to fix a viewpoint)
"""

from __future__ import annotations

import argparse
import time
import urllib.parse
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
ART_DIR = _REPO / "assets" / "art"

# THE LOCKED VIEWPOINT — proven to work (the bakery came out perfect 3/4 iso). Forced on EVERY asset incl.
# animals (which otherwise default to a side profile) so the village composites coherently.
STYLE = (
    ", 3/4 top-down isometric view seen from slightly above at a 30 degree angle, on a small rounded base "
    "tile, cozy stylized cartoon mobile game asset in the style of Hay Day and Cozy Grove, soft warm "
    "lighting, part of a cohesive isometric tileset, plain white background, no text, high quality"
)

ASSETS: "dict[str, str]" = {
    "goose": "a cute chubby white goose with an orange beak standing on grass",
    "bakery": "a small cozy bakery cottage with a warm red shingled roof and a chimney",
    "granary": "a round wooden grain silo barn with a domed roof",
    "nest": "a cozy twig bird nest with three white eggs on grass",
    "well": "a round stone water well with a small wooden shingled roof",
    "fence": "a short section of rustic wooden fence with two posts",
    "tree": "a single round lush green tree with a brown trunk on grass",
    "pond": "a small round pond of calm blue water with lily pads and a grassy edge",
    "ground": "a small round grassy island platform tile with soft dirt edges",
}

REFERENCE_PROMPT = (
    "a screenshot of a polished cozy farm-island mobile game like Hay Day, 3/4 top-down isometric, lush "
    "island with well-spaced cute buildings and animals, warm lighting, high production value, no UI"
)


def build_prompt(desc: str) -> str:
    """A description + the locked isometric style. Pure — unit-tested offline."""
    return desc.strip() + STYLE


def flux_request(prompt: str, seed: int, w: int = 768, h: int = 768, retries: int = 8) -> "bytes | None":
    """Fetch one image from Pollinations FLUX (keyless). Patient backoff for the anonymous 429/500 limits."""
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width={w}&height={h}&nologo=true&model=flux&seed={seed}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(retries):
        try:
            data = urllib.request.urlopen(req, timeout=120).read()
            if len(data) > 3000:
                return data
        except Exception:  # noqa: BLE001 -- rate limit / transient; back off and retry
            pass
        time.sleep(8 * (attempt + 1))
    return None


def generate(name: str, seed: int, *, cut: bool = True, space: float = 25.0) -> bool:
    """Generate one asset -> assets/art/flux_<name>.png (transparent). Returns True on success."""
    from ops.generate_art import cutout
    data = flux_request(build_prompt(ASSETS[name]), seed)
    if not data:
        return False
    if cut and name != "ground":
        try:
            data = cutout(data)
        except Exception:  # noqa: BLE001
            pass
    ART_DIR.mkdir(parents=True, exist_ok=True)
    (ART_DIR / f"flux_{name}.png").write_bytes(data)
    time.sleep(space)                       # respect the anonymous rate limit
    return True


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args(argv)
    names = args.only or list(ASSETS)
    ok = 0
    for i, name in enumerate(names):
        if name not in ASSETS:
            print(f"unknown asset {name}"); continue
        if generate(name, seed=200 + i):
            print(f"{name}: OK"); ok += 1
        else:
            print(f"{name}: FAILED (rate limit) — rerun `--only {name}`")
    from ops.gemini_art import make_contact_sheet
    sheet = make_contact_sheet(ART_DIR / "review_sheet.png", list(ASSETS), prefix="flux_")
    if sheet:
        print(f"review sheet -> {sheet}")
    print(f"generated {ok}/{len(names)}")
    return 0 if ok == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
