"""Deterministic *computer-vision* checks — the STRUCTURAL/DYNAMIC tiers of Stage A.

The past failure these exist to kill: a "visual gate" that was blind, so blank, tiny, or
corrupt art sailed through. These are not taste judgements (that is Stage B's job) — they are
the mechanical floor below which art is objectively broken: it must decode, it must be big
enough to matter, and it must not be a flat fill.

Pillow is imported lazily inside ``run`` so importing this module never breaks the
stdlib-only core on a machine without Pillow; the checks simply cannot certify there. Each
check SKIPs when the artifact ships no images, so a code-only ticket is unaffected. The
higher-is-better metrics (`image_min_dim`, `image_min_stddev`) are emitted for the ratchet:
once accepted at some sharpness, the art can never silently regress below it.
"""

from __future__ import annotations

from pathlib import Path

from harness.checks.base import Check, CheckCost
from harness.models import CheckResult, Result, Ticket

_FIXTURES = Path(__file__).parent / "fixtures"
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
_IGNORE = {"decision_log.jsonl"}

# Objective floors. Below these an asset is broken, not merely mediocre.
MIN_DIMENSION = 32       # px on the shorter side
MIN_STDDEV = 2.0         # grayscale std; a flat fill is ~0


def _images(artifact_dir: Path) -> list[Path]:
    return [
        f for f in sorted(artifact_dir.rglob("*"))
        if f.is_file() and f.suffix.lower() in _IMAGE_SUFFIXES and f.name not in _IGNORE
    ]


class ImageLoadableCheck(Check):
    """Every image file must actually decode. A truncated or mislabelled ``.png`` FAILs."""

    id = "image_loadable"
    targets: list[str] = ["*"]
    cost = CheckCost.STRUCTURAL

    def __init__(self) -> None:
        base = _FIXTURES / "image_loadable"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        from PIL import Image  # lazy: keeps the core importable without Pillow

        imgs = _images(Path(artifact_dir))
        if not imgs:
            return CheckResult(self.id, Result.SKIP, "no image files in artifact")
        for f in imgs:
            try:
                with Image.open(f) as im:
                    im.verify()  # detects truncation/corruption without full decode
            except Exception as e:  # Pillow raises many types for bad images
                return CheckResult(
                    self.id, Result.FAIL, f"{f.name}: not a decodable image: {e}",
                    artifacts=[str(f)],
                )
        return CheckResult(
            self.id, Result.PASS, f"{len(imgs)} image(s) decode",
            artifacts=[str(p) for p in imgs[:5]], metrics={"image_count": float(len(imgs))},
        )


class ImageMinResolutionCheck(Check):
    """Every image's shorter side must be >= ``MIN_DIMENSION`` px. Emits ``image_min_dim``."""

    id = "image_min_resolution"
    targets: list[str] = ["*"]
    cost = CheckCost.STRUCTURAL

    def __init__(self) -> None:
        base = _FIXTURES / "image_min_resolution"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        from PIL import Image

        imgs = _images(Path(artifact_dir))
        if not imgs:
            return CheckResult(self.id, Result.SKIP, "no image files in artifact")
        min_dim = None
        for f in imgs:
            try:
                with Image.open(f) as im:
                    w, h = im.size
            except Exception as e:
                return CheckResult(self.id, Result.FAIL, f"{f.name}: unreadable: {e}",
                                   artifacts=[str(f)])
            side = min(w, h)
            min_dim = side if min_dim is None else min(min_dim, side)
            if side < MIN_DIMENSION:
                return CheckResult(
                    self.id, Result.FAIL,
                    f"{f.name}: {w}x{h} below min short side {MIN_DIMENSION}px",
                    artifacts=[str(f)],
                )
        return CheckResult(
            self.id, Result.PASS, f"all {len(imgs)} image(s) >= {MIN_DIMENSION}px (min {min_dim})",
            metrics={"image_min_dim": float(min_dim)},
        )


class ImageNotBlankCheck(Check):
    """Every image must have real pixel variance — a flat/solid fill FAILs.

    Uses grayscale standard deviation (Pillow ``ImageStat``), no numpy. Emits the minimum
    observed stddev as ``image_min_stddev`` for the ratchet.
    """

    id = "image_not_blank"
    targets: list[str] = ["*"]
    cost = CheckCost.DYNAMIC

    def __init__(self) -> None:
        base = _FIXTURES / "image_not_blank"
        self.good_fixtures = [base / "good"]
        self.bad_fixtures = [base / "bad"]

    def run(self, artifact_dir: Path, ticket: Ticket) -> CheckResult:
        from PIL import Image, ImageStat

        imgs = _images(Path(artifact_dir))
        if not imgs:
            return CheckResult(self.id, Result.SKIP, "no image files in artifact")
        min_std = None
        for f in imgs:
            try:
                with Image.open(f) as im:
                    std = ImageStat.Stat(im.convert("L")).stddev[0]
            except Exception as e:
                return CheckResult(self.id, Result.FAIL, f"{f.name}: unreadable: {e}",
                                   artifacts=[str(f)])
            min_std = std if min_std is None else min(min_std, std)
            if std <= MIN_STDDEV:
                return CheckResult(
                    self.id, Result.FAIL,
                    f"{f.name}: near-flat image (stddev {std:.2f} <= {MIN_STDDEV})",
                    artifacts=[str(f)],
                )
        return CheckResult(
            self.id, Result.PASS, f"all {len(imgs)} image(s) have variance (min stddev {min_std:.2f})",
            metrics={"image_min_stddev": float(min_std)},
        )
