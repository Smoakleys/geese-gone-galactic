"""Vision-on-render scene review — does a rendered scene actually READ as a One Pond scene?

The plan's see-screenshot judge (Part 2B, verifier breadth): show the RENDER to the local vision model and
check it recognises real game elements, not abstract shapes. This became viable only once the props are
genuinely modelled -- the OLD blob art was described as "a green square with a blue square and an orange
shape" (0 concepts); the new village is described as "swans, nests, trees, houses, and a small water body"
(4 concept categories). See docs/SCORECARD.md + memory ggg-abstract-visuals-fail-judges.

The recognition CORE (`concepts_in` / `reads_as_pond_scene`) is a pure, deterministic keyword classifier
over a description string, unit-tested without the model. `review_render` wires it to the real (slow,
stochastic) vision model, so it's an opt-in tool for Icarus / an advisory gate, not a per-commit blocker.
"""

from __future__ import annotations

# Concept categories a real One Pond render should evoke. Recognising >=2 distinct categories means the
# scene reads as a place with waterfowl/structures, not an abstract arrangement of coloured shapes.
_CONCEPTS: "dict[str, tuple[str, ...]]" = {
    "waterfowl": ("goose", "geese", "swan", "duck", "bird", "waterfowl", "gosling"),
    "water": ("pond", "water", "lake", "pool", "river", "puddle"),
    "structure": ("house", "hut", "home", "building", "cottage", "barn", "silo", "roof", "village",
                  "well", "fence", "nest"),
    "nature": ("tree", "grass", "field", "meadow", "greenery", "bush", "garden", "rural", "farm"),
}


def concepts_in(description: str) -> "set[str]":
    """The concept categories a description mentions (case-insensitive substring match)."""
    d = (description or "").lower()
    return {cat for cat, words in _CONCEPTS.items() if any(w in d for w in words)}


def reads_as_pond_scene(description: str, *, min_categories: int = 2) -> "tuple[bool, set[str]]":
    """(ok, matched-categories). OK when the description evokes >= ``min_categories`` distinct game concepts
    -- so an abstract "green square with a blue square and an orange shape" (0) fails, while "swans, nests,
    trees and houses by the water" (4) passes. Lenient on purpose: it gates RECOGNISABILITY, not art taste."""
    cats = concepts_in(description)
    return (len(cats) >= min_categories, cats)


def review_render(png_path: str, vision, *, min_categories: int = 2,
                  question: str = "Describe this image in one sentence. What creatures, buildings, and "
                                  "scenery do you see?") -> "tuple[bool, str]":
    """Ask the vision model to describe the render, then classify recognisability. Returns (ok, detail).
    Never raises -- a vision failure is a non-recognition (ok=False with the reason), so a caller can treat
    it as advisory. ``vision`` is any object with ``describe(image_path, question) -> str``."""
    try:
        desc = vision.describe(png_path, question) or ""
    except Exception as e:  # the model being down is an observation, not a crash
        return False, f"vision unavailable: {type(e).__name__}: {e}"
    ok, cats = reads_as_pond_scene(desc, min_categories=min_categories)
    tag = "reads as a pond scene" if ok else "does NOT read as a pond scene"
    return ok, f"{tag} ({len(cats)} concepts: {sorted(cats)}) — vision said: {desc.strip()[:200]}"
