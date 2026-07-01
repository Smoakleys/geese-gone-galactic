"""The visual gate — a *seeing* gate, decomposed and reference-anchored.

The documented past failure this kills: a visual gate that was effectively blind, so blank or
off-model art passed. The gate here never asks one vague "does this look good?" It:

1. **Decomposes** the judgement into independent, measurable signals (variance, resolution,
   edge coherence, palette, aspect) — ``extract_signals``.
2. **Anchors to a reference** — every signal is scored against the ticket's reference image,
   not judged in a vacuum — ``ReferenceAnchoredScorer``.
3. Is **validated on a labeled set** — the scorer must correctly classify a committed
   good/bad image set before it is trusted (``evaluate_labeled_set``); this is verification
   item 7. A scorer that can't tell the labeled bad art from the good has no business gating.

This CV layer is deterministic and runs with zero model cost. It is the mechanical floor of
Stage B; the model reviewer (``LLMReviewer`` / ``ConsensusReviewer``) supplies the subjective
judgement above it. Both must pass — CV catches blind spots models share, models catch
semantics CV can't see.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VisualSignals:
    width: int
    height: int
    stddev: float          # grayscale variance; ~0 == flat fill
    edge_density: float    # fraction of strong-edge pixels; ~0 blank, ~1 noise
    distinct_colors: int
    aspect: float          # width / height

    @property
    def min_dim(self) -> int:
        return min(self.width, self.height)


def extract_signals(image_path: Path) -> VisualSignals:
    from PIL import Image, ImageFilter, ImageStat

    with Image.open(image_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        gray = im.convert("L")
        stddev = ImageStat.Stat(gray).stddev[0]
        edges = gray.filter(ImageFilter.FIND_EDGES)
        hist = edges.histogram()
        total = float(w * h) or 1.0
        strong = sum(count for value, count in enumerate(hist) if value >= 40)
        edge_density = strong / total
        distinct = len(im.getcolors(maxcolors=1 << 24) or [])
    return VisualSignals(w, h, stddev, edge_density, distinct, w / h if h else 0.0)


def grayscale_histogram(image_path: Path, bins: int = 32) -> list[float]:
    """Normalized ``bins``-bucket grayscale histogram (sums to 1)."""
    from PIL import Image

    with Image.open(image_path) as im:
        hist = im.convert("L").histogram()[:256]
    step = 256 // bins
    buckets = [sum(hist[i * step:(i + 1) * step]) for i in range(bins)]
    total = float(sum(buckets)) or 1.0
    return [b / total for b in buckets]


def histogram_similarity(a: Path, b: Path, bins: int = 32) -> float:
    """Histogram-intersection similarity in [0, 1] (1 == identical tonal distribution)."""
    ha, hb = grayscale_histogram(a, bins), grayscale_histogram(b, bins)
    return sum(min(x, y) for x, y in zip(ha, hb))


@dataclass(frozen=True)
class VisualVerdict:
    passed: bool
    score: float
    reasons: list[str]


class ReferenceAnchoredScorer:
    """Scores an artifact image against a reference and objective floors.

    A PASS requires all of: adequate resolution, real variance (not blank), *coherent* edges
    (structure — not a flat fill and not pure noise), and tonal similarity to the reference
    above ``hist_threshold``. Each is a decomposed, independently-failable reason, so a reject
    always names what was wrong.
    """

    def __init__(self, *, min_dim: int = 32, min_stddev: float = 2.0,
                 edge_lo: float = 0.005, edge_hi: float = 0.40,
                 hist_threshold: float = 0.55):
        self.min_dim = min_dim
        self.min_stddev = min_stddev
        self.edge_lo = edge_lo
        self.edge_hi = edge_hi
        self.hist_threshold = hist_threshold

    def score(self, artifact: Path, reference: Path | None = None) -> VisualVerdict:
        sig = extract_signals(artifact)
        reasons: list[str] = []

        if sig.min_dim < self.min_dim:
            reasons.append(f"resolution {sig.width}x{sig.height} below {self.min_dim}px")
        if sig.stddev <= self.min_stddev:
            reasons.append(f"near-flat image (stddev {sig.stddev:.2f})")
        if sig.edge_density < self.edge_lo:
            reasons.append(f"no structure (edge density {sig.edge_density:.3f} too low)")
        if sig.edge_density > self.edge_hi:
            reasons.append(f"noise, not form (edge density {sig.edge_density:.3f} too high)")

        hist_sim = 1.0
        if reference is not None:
            hist_sim = histogram_similarity(artifact, reference)
            if hist_sim < self.hist_threshold:
                reasons.append(f"off-reference palette (similarity {hist_sim:.2f} "
                               f"< {self.hist_threshold})")

        structural = (self.min_dim <= sig.min_dim and sig.stddev > self.min_stddev
                      and self.edge_lo <= sig.edge_density <= self.edge_hi)
        # Blend the reference similarity with a structural pass/fail into a single score.
        score = round(hist_sim * (1.0 if structural else 0.4), 4)
        return VisualVerdict(passed=not reasons, score=score, reasons=reasons)


@dataclass(frozen=True)
class LabeledSetResult:
    total: int
    correct: int
    false_pass: list[str]   # bad images the scorer wrongly PASSed (the dangerous errors)
    false_fail: list[str]   # good images the scorer wrongly FAILed

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def evaluate_labeled_set(scorer: ReferenceAnchoredScorer, labeled_dir: Path,
                         reference: Path | None = None) -> LabeledSetResult:
    """Run ``scorer`` over ``labeled_dir/{good,bad}`` and report how well it classifies.

    This is how a visual scorer earns trust (verification item 7): it must PASS the good set
    and FAIL the bad set. A false PASS on bad art is the failure mode that historically let
    junk through, so it is reported separately and is what tests assert on.
    """
    labeled_dir = Path(labeled_dir)
    good = sorted((labeled_dir / "good").glob("*")) if (labeled_dir / "good").exists() else []
    bad = sorted((labeled_dir / "bad").glob("*")) if (labeled_dir / "bad").exists() else []
    correct = 0
    false_pass: list[str] = []
    false_fail: list[str] = []
    for img in good:
        if scorer.score(img, reference).passed:
            correct += 1
        else:
            false_fail.append(img.name)
    for img in bad:
        if not scorer.score(img, reference).passed:
            correct += 1
        else:
            false_pass.append(img.name)
    return LabeledSetResult(len(good) + len(bad), correct, false_pass, false_fail)
