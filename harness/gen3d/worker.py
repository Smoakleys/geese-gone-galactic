"""The text-to-3D worker contract + offline-runnable implementations.

Every generator returns an ``Asset``: a mesh file plus a rendered ``preview`` image the visual
gate can score. That preview is the bridge that lets a 2D CV gate judge a 3D generator's
output without a full 3D pipeline — good enough to *select between* generators and to fall
back when one is bad.

Implementations here:
* ``CuratedPackWorker`` — the always-available fallback: copies a vetted low-poly mesh +
  preview from a committed pack. Deterministic and offline; can never fail to produce.
* ``ProceduralStubWorker`` — stands in for a real GPU model of a given ``quality`` so
  selection logic can be exercised (a low-quality worker produces art the gate rejects).
* ``RemoteGpuWorker`` — the real seam: POSTs the prompt to a GPU host and writes back the
  returned mesh/preview. Imported lazily, never touched by the test suite.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

_CURATED = Path(__file__).parent / "curated"

# Palette shared with the Phase-2 visual reference so curated previews read as on-model.
_BG = (34, 139, 34)
_WALL = (210, 180, 140)
_ROOF = (139, 69, 19)


@dataclass
class Asset:
    mesh_path: str
    preview_path: str
    tags: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@runtime_checkable
class MeshGenerator(Protocol):
    model_id: str

    def generate(self, prompt: str, out_dir: Path) -> Asset: ...


def _draw_building(path: Path, *, bg=_BG, wall=_WALL, roof=_ROOF, size=(128, 128)) -> None:
    from PIL import Image, ImageDraw

    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    cx, cy = size[0] // 2, size[1] // 2
    w, h = 56, 44
    x0, y0 = cx - w // 2, cy - h // 2
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=wall, outline=(90, 70, 50))
    d.polygon([(x0 - 4, y0), (x0 + w + 4, y0), (cx, y0 - 22)], fill=roof)
    d.rectangle([cx - 6, y0 + h - 16, cx + 6, y0 + h], fill=(90, 60, 30))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def _unit_cube_obj() -> str:
    return (
        "# minimal low-poly cube\n"
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nv 0 0 1\nv 1 0 1\nv 1 1 1\nv 0 1 1\n"
        "f 1 2 3 4\nf 5 6 7 8\nf 1 2 6 5\nf 2 3 7 6\nf 3 4 8 7\nf 4 1 5 8\n"
    )


class CuratedPackWorker(MeshGenerator):
    """Guaranteed fallback. Serves a vetted mesh+preview from the committed curated pack."""

    model_id = "curated-pack"

    def __init__(self, pack_dir: Path | None = None):
        self._pack = Path(pack_dir or _CURATED)

    def generate(self, prompt: str, out_dir: Path) -> Asset:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        entry = self._match(prompt)
        mesh_src = entry / "mesh.obj"
        prev_src = entry / "preview.png"
        mesh_dst = out_dir / "mesh.obj"
        prev_dst = out_dir / "preview.png"
        shutil.copy2(mesh_src, mesh_dst)
        shutil.copy2(prev_src, prev_dst)
        return Asset(str(mesh_dst), str(prev_dst), tags=[entry.name],
                     meta={"source": "curated", "prompt": prompt})

    def _match(self, prompt: str) -> Path:
        entries = [p for p in sorted(self._pack.iterdir()) if p.is_dir()] if self._pack.exists() else []
        for e in entries:
            if e.name in prompt.lower():
                return e
        if entries:
            return entries[0]
        raise FileNotFoundError(f"curated pack empty at {self._pack}")


class ProceduralStubWorker(MeshGenerator):
    """Simulates a GPU generator whose output quality is ``quality`` in [0, 1].

    High quality draws an on-model building the gate accepts; low quality draws a flat fill the
    gate rejects — so selection logic (pick the good generator, fall back when all fail) is
    testable without a GPU.
    """

    def __init__(self, model_id: str = "stub-gpu", quality: float = 1.0):
        self.model_id = model_id
        self.quality = quality

    def generate(self, prompt: str, out_dir: Path) -> Asset:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        mesh = out_dir / "mesh.obj"
        mesh.write_text(_unit_cube_obj())
        preview = out_dir / "preview.png"
        if self.quality >= 0.5:
            _draw_building(preview)
        else:
            from PIL import Image
            Image.new("RGB", (128, 128), _BG).save(preview)  # flat fill -> gate rejects
        return Asset(str(mesh), str(preview), tags=[prompt.split()[0] if prompt else "asset"],
                     meta={"source": self.model_id, "quality": self.quality})


class RemoteGpuWorker(MeshGenerator):  # pragma: no cover - real GPU seam, not unit tested
    """Real seam: POST a prompt to a GPU host, write back the returned mesh + preview."""

    def __init__(self, endpoint: str, model_id: str = "remote-gpu", timeout: float = 300.0):
        self.endpoint = endpoint
        self.model_id = model_id
        self.timeout = timeout

    def generate(self, prompt: str, out_dir: Path) -> Asset:
        import json
        import urllib.request

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            self.endpoint, method="POST",
            data=json.dumps({"prompt": prompt}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read())
        mesh = out_dir / "mesh.obj"
        preview = out_dir / "preview.png"
        mesh.write_bytes(bytes.fromhex(payload["mesh_hex"]))
        preview.write_bytes(bytes.fromhex(payload["preview_hex"]))
        return Asset(str(mesh), str(preview), tags=payload.get("tags", []),
                     meta={"source": self.model_id, "prompt": prompt})
