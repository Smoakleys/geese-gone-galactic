"""Generate game art with Google's Gemini image model (Nano Banana / gemini image) -- FREE tier.

Bridger's call: use Gemini with VERY strict prompts for coherent, high-quality game art (Pollinations gated
its good models + is unreliable). The free Google AI Studio key (aistudio.google.com/apikey -- no billing,
no card) drives the Generative Language API's image models. This module holds a LOCKED-VIEWPOINT prompt
style so every asset shares one camera/perspective/light (the fix for "wrong viewpoints"), and generates
into assets/art/.

Key (gitignored, never committed), first found wins:
  * env  GEMINI_API_KEY
  * ops/gemini_config.local.json  ->  {"api_key": "..."}   (or a bare key in ops/gemini_key.local.txt)

Usage:
    python ops/gemini_art.py --only goose bakery          # generate specific props
    python ops/gemini_art.py --check                      # just verify the key + endpoint

The prompt-building + key-loading are unit-tested offline; the network call needs the key.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
ART_DIR = _REPO / "assets" / "art"
_CONFIG = _REPO / "ops" / "gemini_config.local.json"
_KEYFILE = _REPO / "ops" / "gemini_key.local.txt"

# Model: Nano Banana / Gemini image generation (verified current ID, 2026). Overridable via config "model".
DEFAULT_MODEL = "gemini-2.5-flash-image"

# THE LOCKED VIEWPOINT/STYLE -- appended to every prompt so all assets share one camera + light + look,
# the fix for the incoherent "wrong viewpoints" (side-goose + 3/4-building + top-down-pond). See memory
# visual-review-discipline.
STYLE = (
    ", single game asset, 3/4 top-down isometric view at a consistent 30-degree camera angle, orthographic "
    "projection, soft lighting coming from the top-left, cozy stylized cartoon mobile-game art (Hay Day / "
    "Cozy Grove style), clean crisp shapes, centered, plain flat white background, no ground shadow, no "
    "other objects, no text, high quality, cohesive tileset"
)

# A REAL reference screenshot to grade my output against (visual-review-discipline step 2: never judge in a
# vacuum). Deliberately NOT the single-asset style -- a full polished scene, so I compare composition + scale.
REFERENCE_PROMPT = (
    "a screenshot of a polished professional cozy farm-island mobile game like Hay Day or Cozy Grove, "
    "3/4 top-down isometric, lush island with well-spaced cute buildings, animals, and trees, warm soft "
    "lighting, high production value, no text or UI overlay"
)

# Each prop, described the SAME way (one perspective) so a village composites coherently.
ASSETS: "dict[str, str]" = {
    "goose": "a plump friendly white cartoon goose with an orange beak",
    "bakery": "a small cozy bakery cottage with a warm red shingled roof and a chimney",
    "granary": "a round wooden grain silo with a domed roof",
    "nest": "a twig bird nest with three white eggs",
    "well": "a round stone water well with a small wooden shingled roof",
    "fence": "a short section of rustic wooden fence with two posts and a rail",
    "tree": "a single round lush green tree with a brown trunk",
    "pond": "a small round pond of calm blue water with lily pads",
    "ground": "a small round grassy island tile with soft dirt edges",
}


def load_key() -> "str | None":
    """The free Gemini API key, from env or a gitignored local file. None if not configured."""
    import os
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    if _CONFIG.is_file():
        try:
            return str(json.loads(_CONFIG.read_text()).get("api_key", "")).strip() or None
        except (json.JSONDecodeError, OSError):
            return None
    if _KEYFILE.is_file():
        return _KEYFILE.read_text(encoding="utf-8").strip() or None
    return None


def model_id() -> str:
    if _CONFIG.is_file():
        try:
            return str(json.loads(_CONFIG.read_text()).get("model") or DEFAULT_MODEL)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_MODEL


def build_prompt(desc: str) -> str:
    """A description + the locked viewpoint/style. Kept pure for testing."""
    return desc.strip() + STYLE


def _image_request(prompt: str, key: str, model: str, timeout: float, retries: int = 3) -> bytes:
    """POST a prompt to the Gemini image API, with backoff; returns raw PNG bytes or raises."""
    import time
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}")
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}   # docs order
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "ggg"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            raise ValueError("no image in response")
        except urllib.error.HTTPError as e:
            # a 4xx (bad/typo'd key, bad request, quota) won't recover on retry -> fail FAST + clear
            if 400 <= e.code < 500:
                detail = f"HTTP {e.code} — check the key/quota (a 4xx won't succeed on retry)"
                raise RuntimeError(detail) from e
            last = e                                          # 5xx is transient -> retry
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
        except Exception as e:  # noqa: BLE001 -- network/parse hiccup; back off + retry
            last = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise last if last else RuntimeError("image request failed")


def generate(desc: str, out_png: Path, key: str, *, model: "str | None" = None, timeout: float = 120.0,
             cut: bool = True) -> bool:
    """Generate one asset via the Gemini image API (locked viewpoint). Cuts the white background to
    transparency so it's composite-ready (the prompt asks for a plain white bg). Returns True on success."""
    data = _image_request(build_prompt(desc), key, model or model_id(), timeout)
    if cut:
        try:
            from ops.generate_art import cutout
            data = cutout(data)                           # flood-fill the white border -> transparent
        except Exception:  # noqa: BLE001 -- if cutout fails, keep the raw image rather than lose it
            pass
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(data)
    return True


def generate_reference(out_png: Path, key: str, *, model: "str | None" = None, timeout: float = 120.0) -> bool:
    """Generate a REAL cozy-game reference screenshot to grade my composited scene against (the discipline)."""
    data = _image_request(REFERENCE_PROMPT, key, model or model_id(), timeout)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(data)
    return True


def make_contact_sheet(out_png: Path, names: "list[str] | None" = None) -> "Path | None":
    """Tile the generated gemini_<name> assets (+ reference if present) into ONE labelled review image, so I
    can grade them against the reference on the rubric in a single view (visual-review-discipline). Returns
    the path, or None if no assets exist yet."""
    from PIL import Image, ImageDraw
    names = names or list(ASSETS)
    tiles = []
    for n in names:
        p = ART_DIR / f"gemini_{n}.png"
        if p.is_file():
            tiles.append((n, p))
    ref = ART_DIR / "reference_game.png"
    if ref.is_file():
        tiles.append(("REFERENCE", ref))
    if not tiles:
        return None
    cell, cols = 240, 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (235, 235, 235, 255))
    d = ImageDraw.Draw(sheet)
    for i, (label, p) in enumerate(tiles):
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:  # noqa: BLE001
            continue
        im.thumbnail((cell - 16, cell - 32))
        x, y = (i % cols) * cell, (i // cols) * cell
        sheet.alpha_composite(im, (x + (cell - im.width) // 2, y + 20))
        d.text((x + 6, y + 4), label, fill=(20, 20, 20, 255))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out_png)
    return out_png


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--reference", action="store_true", help="also generate a real-game reference to grade against")
    args = ap.parse_args(argv)
    key = load_key()
    if not key:
        print("NO KEY. Get a FREE one at https://aistudio.google.com/apikey (no billing), then either:\n"
              "  setx GEMINI_API_KEY <key>   (new shell)   OR\n"
              f"  echo <key> > {_KEYFILE}")
        return 2
    if args.check:
        print(f"key loaded ({len(key)} chars); model {model_id()}")
        return 0
    if args.reference:
        try:
            generate_reference(ART_DIR / "reference_game.png", key)
            print("reference: OK -> reference_game.png (compare your scene against this)")
        except Exception as e:  # noqa: BLE001
            print(f"reference: FAILED {type(e).__name__}: {e}")
    names = args.only or list(ASSETS)
    ok = 0
    for name in names:
        if name not in ASSETS:
            print(f"unknown asset {name}"); continue
        try:
            if generate(ASSETS[name], ART_DIR / f"gemini_{name}.png", key):
                print(f"{name}: OK -> gemini_{name}.png"); ok += 1
            else:
                print(f"{name}: no image in response")
        except Exception as e:  # noqa: BLE001
            print(f"{name}: FAILED {type(e).__name__}: {e}")
    print(f"generated {ok}/{len(names)}")
    sheet = make_contact_sheet(ART_DIR / "review_sheet.png", names)
    if sheet:
        print(f"review sheet -> {sheet} (grade these vs the reference on the rubric before committing)")
    return 0 if ok == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
