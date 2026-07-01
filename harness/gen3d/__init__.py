"""Text-to-3D generation behind a swappable worker seam.

The harness must not hard-depend on any one generator: local GPU (TRELLIS/Hunyuan) now or
later, a paid API as fallback, or a curated low-poly pack when nothing else is available. All
of them implement one ``MeshGenerator`` contract, and ``select_generator`` measures their
output quality against the same reference-anchored visual gate used in Stage B — so the
*best passing* generator is chosen by measurement, with the curated pack as a guaranteed
fallback. No GPU is required to run or test any of this; the real GPU worker is a drop-in.
"""

from harness.gen3d.worker import (
    Asset,
    CuratedPackWorker,
    MeshGenerator,
    ProceduralStubWorker,
)
from harness.gen3d.select import SelectionResult, select_generator

__all__ = [
    "Asset",
    "MeshGenerator",
    "CuratedPackWorker",
    "ProceduralStubWorker",
    "SelectionResult",
    "select_generator",
]
