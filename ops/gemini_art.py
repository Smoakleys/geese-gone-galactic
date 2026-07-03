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
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
ART_DIR = _REPO / "assets" / "art"
_CONFIG = _REPO / "ops" / "gemini_config.local.json"
_KEYFILE = _REPO / "ops" / "gemini_key.local.txt"

# Model: Nano Banana / Gemini image generation on the free tier. Overridable via config "model".
DEFAULT_MODEL = "gemini-2.5-flash-image-preview"

# THE LOCKED VIEWPOINT/STYLE -- appended to every prompt so all assets share one camera + light + look,
# the fix for the incoherent "wrong viewpoints" (side-goose + 3/4-building + top-down-pond). See memory
# visual-review-discipline.
STYLE = (
    ", single game asset, 3/4 top-down isometric view at a consistent 30-degree camera angle, orthographic "
    "projection, soft lighting coming from the top-left, cozy stylized cartoon mobile-game art (Hay Day / "
    "Cozy Grove style), clean crisp shapes, centered, plain flat white background, no ground shadow, no "
    "other objects, no text, high quality, cohesive tileset"
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


def generate(desc: str, out_png: Path, key: str, *, model: "str | None" = None, timeout: float = 120.0) -> bool:
    """Generate one asset via the Gemini image API. Returns True on success (image written)."""
    model = model or model_id()
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}")
    payload = {
        "contents": [{"parts": [{"text": build_prompt(desc)}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "ggg"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            out_png.parent.mkdir(parents=True, exist_ok=True)
            out_png.write_bytes(base64.b64decode(inline["data"]))
            return True
    return False


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--check", action="store_true")
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
    return 0 if ok == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
